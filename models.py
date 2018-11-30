import json
import logging
import os
import uuid
from functools import reduce
from tempfile import TemporaryDirectory

import fiona
import fiona.transform
from deepmerge import always_merger
from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.contrib.postgres.fields import JSONField
from django.core.serializers import serialize
from django.db import connection, transaction
from django.db.models import F, Manager
from django.utils.functional import cached_property
from fiona.crs import from_epsg
from mercantile import tiles

from terracommon.core.helpers import make_zipfile_bytesio

from .helpers import ChunkIterator
from .managers import FeatureQuerySet
from .tiles.funcs import ST_SRID, ST_HausdorffDistance
from .tiles.helpers import VectorTile, guess_maxzoom, guess_minzoom

logger = logging.getLogger(__name__)

ACCEPTED_PROJECTIONS = [
    'urn:ogc:def:crs:OGC:1.3:CRS84',
    'EPSG:4326',
]


def zoom_update(func):
    def wrapper(*args, **kargs):
        layer = args[0]
        response = func(*args, **kargs)

        try:
            layer.layer_settings('tiles', 'minzoom')
        except KeyError:
            layer.set_layer_settings(
                'tiles', 'minzoom', guess_minzoom(layer))
            layer.save(update_fields=["settings"])

        try:
            layer.layer_settings('tiles', 'maxzoom')
        except KeyError:
            layer.set_layer_settings(
                'tiles', 'maxzoom', guess_maxzoom(layer))
            layer.save(update_fields=["settings"])

        return response
    return wrapper


class Layer(models.Model):
    name = models.CharField(max_length=256, unique=True, default=uuid.uuid4)
    group = models.CharField(max_length=255, default="__nogroup__")
    schema = JSONField(default=dict, blank=True)

    # Settings scheam
    SETTINGS_DEFAULT = {
        # Tilesets attributes
        'tiles': {
            'minzoom': 0,
            'maxzoom': 22,
            'pixel_buffer': 4,
            'features_filter': None,  # Json
            'properties_filter': None,  # Array of string
            'features_limit': 10000,
        }
    }
    settings = JSONField(default=dict, blank=True)

    def _initial_import_from_csv(self, chunks, options, operations):
        for chunk in chunks:
            entries = []
            for row in chunk:
                feature_args = {
                    "geom": None,
                    "properties": row,
                    "layer": self
                }

                for operation in operations:
                    operation(feature_args, options)

                if not feature_args.get("geom"):
                    logger.warning('empty geometry,'
                                   f' row skipped : {row}')
                    continue

                entries.append(
                    Feature(**feature_args)
                )
            Feature.objects.bulk_create(entries)

    def _complementary_import_from_csv(self, chunks, options, operations,
                                       pk_properties, fast=False):
        for chunk in chunks:
            sp = None
            if fast:
                sp = transaction.savepoint()
            for row in chunk:
                self._import_row_from_csv(row, pk_properties, operations,
                                          options)
            if sp:
                transaction.savepoint_commit(sp)

    def _import_row_from_csv(self, row, pk_properties, operations, options):
        feature_args = {
            "geom": None,
            "properties": row,
            "layer": self
        }
        for operation in operations:
            operation(feature_args, options)
        filter_kwargs = {
            f'properties__{p}': feature_args["properties"].get(p, '')
            for p in pk_properties}
        filter_kwargs['layer'] = feature_args.get("layer", self)
        if feature_args.get("geom"):
            Feature.objects.update_or_create(
                defaults=feature_args,
                **filter_kwargs
            )
        else:
            try:
                Feature.objects.filter(**filter_kwargs).update(
                    **{'properties': feature_args["properties"]})
            except Feature.DoesNotExist:
                logger.warning('feature does not exist,'
                               ' empty geometry,'
                               f' row skipped : {row}')

    @zoom_update
    def from_csv_dictreader(self, reader, pk_properties, options, operations,
                            init=False, chunk_size=1000, fast=False):
        """Import (create or update) features from csv.DictReader object
        :param reader: csv.DictReader object
        :param pk_properties: keys of row that is used to identify unicity
        :param init: allow to speed up import if there is only new Feature's
                    (no updates)
        :param chunk_size: only used if init=True, control the size of
                           bulk_create
        """
        chunks = ChunkIterator(reader, chunk_size)
        if init:
            self._initial_import_from_csv(
                chunks=chunks,
                options=options,
                operations=operations
            )
        else:
            self._complementary_import_from_csv(
                chunks=chunks,
                options=options,
                operations=operations,
                pk_properties=pk_properties,
                fast=fast
            )

    @zoom_update
    def from_geojson(self, geojson_data, id_field=None, update=False):
        """
        Import geojson raw data in a layer
        Args:
            geojson_data(str): must be raw text json data
        """
        geojson = json.loads(geojson_data)
        projection = geojson.get('crs', {}).get(
            'properties', {}).get('name', None)
        if projection and not self.is_projection_allowed(projection):
            raise GEOSException(
                f'GeoJSON projection {projection} must be in '
                f'{ACCEPTED_PROJECTIONS}')

        if update:
            self.features.all().delete()
        for feature in geojson.get('features', []):
            properties = feature.get('properties', {})
            identifier = properties.get(id_field, uuid.uuid4())
            Feature.objects.create(
                layer=self,
                identifier=identifier,
                properties=properties,
                geom=GEOSGeometry(json.dumps(feature.get('geometry'))),
            )

    def to_geojson(self):
        return json.loads(serialize('geojson',
                                    self.features.all(),
                                    fields=('properties',),
                                    geometry_field='geom',
                                    properties_field='properties'))

    def to_shapefile(self):

        schema = {
            'geometry': self.layer_geometry,
            'properties': self.layer_properties,
        }

        if not self.features.count():
            return

        with TemporaryDirectory() as shape_folder:
            with fiona.open(
                    os.path.join(shape_folder, 'shape.shp'),
                    mode='w',
                    driver='ESRI Shapefile',
                    schema=schema,
                    crs=from_epsg(self.layer_projection)) as shapefile:
                for feature in self.features.all():
                    shapefile.write({
                        'geometry': json.loads(feature.geom.json),
                        'properties': {
                                prop: json.dumps(feature.properties.get(prop))
                                for prop in self.layer_properties
                            }
                        })
            return make_zipfile_bytesio(shape_folder)

    def _fiona_shape_projection(self, shape):
        ''' Return projection in EPSG format or raw Proj format extracted from
            shape
        '''
        projection = shape.crs
        if projection and (len(projection) == 1 or
           (len(projection) == 2 and projection.get('no_defs') is True)):
            return projection.get('init')
        else:
            return fiona.crs.to_string(projection)

    @zoom_update
    def from_shapefile(self, zipped_shapefile_file, id_field=None):
        ''' Load ShapeFile content provided into a zipped archive.

        zipped_shapefile_file -- a file-like object on the zipped content
        id_field -- the field name used a identifier
        '''
        with fiona.BytesCollection(zipped_shapefile_file.read()) as shape:
            # Extract source projection and compute if reprojection is required
            projection = self._fiona_shape_projection(shape)
            reproject = projection and \
                not self.is_projection_allowed(projection.upper())

            for feature in shape:
                properties = {}
                for prop, value in feature.get('properties', {}).items():
                    try:
                        properties[prop] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        properties[prop] = value

                geometry = feature.get('geometry')

                if reproject:
                    geometry = fiona.transform.transform_geom(
                        shape.crs,
                        f'EPSG:{settings.INTERNAL_GEOMETRY_SRID}',
                        geometry)
                identifier = properties.get(id_field, uuid.uuid4())

                Feature.objects.create(
                    layer=self,
                    identifier=identifier,
                    properties=properties,
                    geom=GEOSGeometry(json.dumps(geometry)),
                )

    @transaction.atomic
    def update_geometries(self, features):
        modified = self.features.none()
        for new_feature in features:
            geometry = GEOSGeometry(json.dumps(new_feature['geometry']))
            nearest_feature = (
                self.features
                    .filter(geom__bboverlaps=geometry)  # Bounding Box Overlap
                    .annotate(hausdorff=ST_HausdorffDistance('geom',
                                                             geometry.ewkb))
                    .order_by('hausdorff')
                    .first()
            )
            feature = self.features.filter(pk=nearest_feature.pk)
            feature.update(properties=new_feature.get('properties', {}))
            modified |= feature
        # clean cache of updated features
        [feature.clean_vect_tile_cache() for feature in modified]
        return modified

    @cached_property
    def layer_projection(self):
        feature = self.features.annotate(srid=ST_SRID(F('geom'))).first()
        return feature.srid

    @cached_property
    def layer_properties(self):
        ''' Return properties of first feature of the layer
        '''
        feature_table = Feature._meta.db_table

        layer_field = Feature._meta.get_field('layer').get_attname_column()[1]

        cursor = connection.cursor()
        raw_query = f"""
                    SELECT
                        jsonb_object_keys(properties) AS key
                    FROM {feature_table}
                    WHERE
                        {layer_field} = %s
                    GROUP BY key;
                    """

        cursor.execute(raw_query, [self.pk, ])

        return {
            prop: 'str'
            for (prop, ) in cursor.fetchall()
        }

    @cached_property
    def layer_geometry(self):
        ''' Return the geometry type of the layer using the first feature in
            the layer
        '''
        feature = self.features.first()
        if feature:
            return feature.geom.geom_type

        return None

    @cached_property
    def settings_with_default(self):
        return always_merger.merge(self.SETTINGS_DEFAULT, self.settings)

    def layer_settings(self, *json_path):
        ''' Return the nested value of settings at path json_path.
            Raise an KeyError if not defined.
        '''
        # Dives into settings using args
        return reduce(
            lambda a, v: a[v],  # Let raise KeyError on missing key
            json_path,
            self.settings) if self.settings is not None else None

    def layer_settings_with_default(self, *json_path):
        ''' Return the nested value of settings with SETTINGS_DEFAULT as
            falback at path json_path.
            Raise an KeyError if not defined.
        '''
        # Dives into settings using args
        return reduce(
            lambda a, v: a[v],  # Let raise KeyError on missing key
            json_path,
            self.settings_with_default)

    def set_layer_settings(self, *json_path_value):
        '''Set last parameter as value at the path place into settings
        '''
        json_path, value = json_path_value[:-1], json_path_value[-1]
        # Dive into settings until the last key of path,
        # the set the value
        settings = self.settings
        for key in json_path[:-1]:
            s = settings.get(key, {})
            settings[key] = s
            settings = s
        settings[json_path[-1]] = value

        try:
            # Delete the cached property
            del self.settings_with_default
        except AttributeError:
            pass  # Let's continue, cache was not set

    def is_projection_allowed(self, projection):
        return projection in ACCEPTED_PROJECTIONS

    class Meta:
        ordering = ['id']
        permissions = (
            ('can_update_features_properties', 'Is able update geometries '
                                               'properties'),
        )


class Feature(models.Model):
    geom = models.GeometryField(srid=settings.INTERNAL_GEOMETRY_SRID)
    identifier = models.CharField(max_length=255,
                                  blank=False,
                                  null=False,
                                  default=uuid.uuid4)
    properties = JSONField()
    layer = models.ForeignKey(Layer,
                              on_delete=models.PROTECT,
                              related_name='features')

    source = models.IntegerField(null=True,
                                 help_text='Internal field used by pgRouting')
    target = models.IntegerField(null=True,
                                 help_text='Internal field used by pgRouting')

    objects = Manager.from_queryset(FeatureQuerySet)()

    def clean_vect_tile_cache(self):
        vtile = VectorTile(self.layer)
        vtile.clean_tiles(
            self.get_intersected_tiles(),
            self.layer.layer_settings_with_default(
                'tiles', 'pixel_buffer'),
            self.layer.layer_settings_with_default(
                'tiles', 'features_filter'),
            self.layer.layer_settings_with_default(
                'tiles', 'properties_filter'),
            self.layer.layer_settings_with_default(
                'tiles', 'features_limit')
        )

    def get_intersected_tiles(self):
        zoom_range = range(settings.MIN_TILE_ZOOM, settings.MAX_TILE_ZOOM + 1)
        try:
            return [(tile.x, tile.y, tile.z)
                    for tile in tiles(*self.get_bounding_box(), zoom_range)]
        except ValueError:
            # TODO find why a ValueError is raised with some Point() geometries
            return []

    def get_bounding_box(self):
        return self.geom.extent

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.clean_vect_tile_cache()

    class Meta:
        ordering = ['id']


class LayerRelation(models.Model):
    origin = models.ForeignKey(Layer,
                               on_delete=models.PROTECT,
                               related_name='relations_as_origin')
    destination = models.ForeignKey(Layer,
                                    on_delete=models.PROTECT,
                                    related_name='relations_as_destination')
    schema = JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']


class FeatureRelation(models.Model):
    origin = models.ForeignKey(Feature,
                               on_delete=models.PROTECT,
                               related_name='relations_as_origin')
    destination = models.ForeignKey(Feature,
                                    on_delete=models.PROTECT,
                                    related_name='relations_as_destination')
    properties = JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']
