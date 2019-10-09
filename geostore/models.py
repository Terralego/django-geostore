import glob
import json
import logging
import os
import uuid
from copy import deepcopy
from functools import reduce
from tempfile import TemporaryDirectory

import fiona
import fiona.transform
from deepmerge import always_merger
from django.contrib.auth.models import Group
from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GistIndex
from django.core.serializers import serialize
from django.db import connection, transaction
from django.db.models import Manager
from django.utils.functional import cached_property
from django.utils.text import slugify
from fiona.crs import from_epsg
from mercantile import tiles

from . import GeometryTypes, settings as app_settings
from .helpers import ChunkIterator, make_zipfile_bytesio
from .managers import FeatureQuerySet
from .mixins import BaseUpdatableModel
from .routing.helpers import Routing
from .tiles.funcs import ST_HausdorffDistance
from .tiles.helpers import VectorTile, guess_maxzoom, guess_minzoom
from .validators import (validate_geom_type, validate_json_schema,
                         validate_json_schema_data)


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
            minzoom = layer.layer_settings('tiles', 'minzoom')
        except KeyError:
            minzoom = guess_minzoom(layer)
            layer.set_layer_settings('tiles', 'minzoom', minzoom)
            layer.save(update_fields=["settings"])

        try:
            layer.layer_settings('tiles', 'maxzoom')
        except KeyError:
            maxzoom = max(guess_maxzoom(layer), minzoom)
            layer.set_layer_settings('tiles', 'maxzoom', maxzoom)
            layer.save(update_fields=["settings"])

        return response
    return wrapper


def topology_update(func):
    def wrapper(layer, *args, **kwargs):
        response = func(layer, *args, **kwargs)
        Routing.create_topology(layer)
        return response

    return wrapper


class Layer(BaseUpdatableModel):
    name = models.CharField(max_length=256, unique=True, default=uuid.uuid4)
    schema = JSONField(default=dict, blank=True, validators=[validate_json_schema])
    geom_type = models.IntegerField(choices=GeometryTypes.choices(), null=True)
    authorized_groups = models.ManyToManyField(Group, blank=True, related_name='authorized_layers')

    # Settings scheam
    SETTINGS_DEFAULT = {
        'metadata': {
            'attribution': None,  # Json, eg. {'name': 'OSM contributors', href='http://openstreetmap.org'}
            'licence': None,  # String, eg. 'ODbL'
            'description': None,  # String
        },
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

    @topology_update
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

    @topology_update
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
            Feature.objects.update_or_create(
                layer=self,
                identifier=identifier,
                defaults={
                    'properties': properties,
                    'geom': GEOSGeometry(json.dumps(feature.get('geometry'))),
                }
            )

    def to_geojson(self):
        return json.loads(serialize('geojson',
                                    self.features.all(),
                                    fields=('properties',),
                                    geometry_field='geom',
                                    properties_field='properties'))

    def to_shapefile(self):

        if not self.features.count():
            return

        with TemporaryDirectory() as shape_folder:
            shapes = {}
            # get all accepted types if geom_type not defined, else keep selected
            type_to_check = GeometryTypes.shape_allowed_type_names()\
                if not self.geom_type else \
                [self.geom_type.name]

            # Create one shapefile by kind of geometry
            for geom_type in type_to_check:
                schema = {
                    'geometry': geom_type,
                    'properties': self.layer_properties,
                }

                shapes[geom_type] = fiona.open(
                    shape_folder,
                    layer=geom_type,
                    mode='w',
                    driver='ESRI Shapefile',
                    schema=schema,
                    encoding='UTF-8',
                    crs=from_epsg(app_settings.INTERNAL_GEOMETRY_SRID)
                )

            # Export features to each kind of geometry
            for feature in self.features.all():
                shapes[feature.geom.geom_type].write({
                    'geometry': json.loads(feature.geom.json),
                    'properties': self._get_serialized_properties(feature.properties)
                })

            # Close fiona files
            for geom_type, shape in shapes.items():
                shape_size = len(shape)
                shape.close()

                # Delete empty shapes
                if not shape_size:
                    for filename in glob.iglob(os.path.join(shape_folder, f'{geom_type}.*')):
                        os.remove(filename)

            # Zip to BytesIO and return shape files
            return make_zipfile_bytesio(shape_folder)

    def _get_serialized_properties(self, feature_properties):
        properties = {k: None for k in self.layer_properties}
        for prop, value in feature_properties.items():
            if isinstance(value, str):
                properties[prop] = value
            else:
                properties[prop] = json.dumps(value)
        return properties

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

    @topology_update
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
                        f'EPSG:{app_settings.INTERNAL_GEOMETRY_SRID}',
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
    def layer_properties(self):
        """
        Return properties based on layer features or layer schema definition
        """
        if self.schema:
            results = list(self.schema.get('properties', {}).keys())

        else:
            feature_table = Feature._meta.db_table

            layer_field = Feature._meta.get_field('layer').get_attname_column()[1]

            cursor = connection.cursor()
            raw_query = f"""
                SELECT
                    jsonb_object_keys(properties) AS key
                FROM
                    (SELECT properties FROM {feature_table} WHERE {layer_field} = %s) AS t
                GROUP BY
                    key;
                """

            cursor.execute(raw_query, [self.pk, ])
            results = [x[0] for x in cursor.fetchall()]

        return {
            prop: 'str'
            for prop in results
        }

    def get_property_title(self, prop):
        """ Get json property title with its name. Return its name if not defined. """
        json_form_properties = self.schema.get('properties', {})

        if prop in json_form_properties:
            data = json_form_properties[prop]
            title = data.get('title', prop)
            return title

        return prop

    def get_property_type(self, prop):
        """ Get json property type with its name """
        prop_type = None
        json_form_properties = self.schema.get('properties', {})

        if prop in json_form_properties:
            data = json_form_properties[prop]
            prop_type = data.get('type')

        return prop_type

    @property
    def is_point(self):
        return self.layer_geometry in (GeometryTypes.Point,
                                       GeometryTypes.MultiPoint)

    @property
    def is_linestring(self):
        return self.layer_geometry in (GeometryTypes.LineString,
                                       GeometryTypes.MultiLineString)

    @property
    def is_polygon(self):
        return self.layer_geometry in (GeometryTypes.Polygon,
                                       GeometryTypes.MultiPolygon)

    @property
    def is_multi(self):
        return self.layer_geometry in (GeometryTypes.MultiPoint,
                                       GeometryTypes.MultiLineString,
                                       GeometryTypes.MultiPolygon)

    @cached_property
    def layer_geometry(self):
        ''' Return the geometry type of the layer using the first feature in
            the layer if the layer have no geom_type or the geom_type of the layer
        '''
        if self.geom_type is None:
            feature = self.features.first()
            if feature:
                return feature.geom.geom_typeid
        return self.geom_type

    @cached_property
    def settings_with_default(self):
        return always_merger.merge(deepcopy(self.SETTINGS_DEFAULT), self.settings)

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
            fallback at path json_path.
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
        # and set the corresponding value
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

    def __str__(self):
        return f"{self.name}"

    class Meta:
        ordering = ['id']
        permissions = (
            ('can_manage_layers', 'Has all permissions on layers'),
            ('can_export_layers', 'Is able to export layers'),
            ('can_import_layers', 'Is able to import layers'),
        )


class LayerGroup(BaseUpdatableModel):
    name = models.CharField(max_length=256, unique=True)
    slug = models.SlugField(unique=True)
    layers = models.ManyToManyField(Layer, related_name='layer_groups')

    def save(self, **kwargs):
        if self.pk is None:
            self.slug = slugify(self.name)
        super().save(**kwargs)


class Feature(BaseUpdatableModel):
    geom = models.GeometryField(srid=app_settings.INTERNAL_GEOMETRY_SRID)
    identifier = models.CharField(max_length=255,
                                  blank=False,
                                  null=False,
                                  default=uuid.uuid4)
    properties = JSONField(default=dict, blank=True)
    layer = models.ForeignKey(Layer,
                              on_delete=models.PROTECT,
                              related_name='features')

    source = models.IntegerField(null=True,
                                 blank=True,
                                 help_text='Internal field used by pgRouting')
    target = models.IntegerField(null=True,
                                 blank=True,
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
        zoom_range = range(app_settings.MIN_TILE_ZOOM, app_settings.MAX_TILE_ZOOM + 1)
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

    def clean(self):
        """
        Validate properties according schema if provided
        """
        validate_geom_type(self.layer.geom_type, self.geom.geom_typeid)
        validate_json_schema_data(self.properties, self.layer.schema)

    class Meta:
        ordering = ['id']
        indexes = [
            models.Index(fields=['layer', ]),
            models.Index(fields=['updated_at', ]),
            models.Index(fields=['updated_at', 'layer', ]),
            models.Index(fields=['identifier', ]),
            GistIndex(fields=['layer', 'geom']),
        ]


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
