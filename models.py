import json
import logging
import os
import uuid
from tempfile import TemporaryDirectory

import fiona
from django.conf import settings
from django.contrib.gis.db import models
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.contrib.postgres.fields import JSONField
from django.core.serializers import serialize
from django.db import transaction
from django.db.models import F, Manager
from django.utils.functional import cached_property
from fiona.crs import from_epsg
from mercantile import tiles

from terracommon.core.helpers import make_zipfile_bytesio

from .fields import DateFieldYearLess
from .helpers import ChunkIterator
from .managers import FeatureQuerySet
from .tiles.funcs import ST_SRID
from .tiles.helpers import VectorTile

logger = logging.getLogger(__name__)

ACCEPTED_PROJECTIONS = [
    'urn:ogc:def:crs:OGC:1.3:CRS84',
    'EPSG:4326',
]


class Layer(models.Model):
    name = models.CharField(max_length=256, unique=True, default=uuid.uuid4)
    group = models.CharField(max_length=255, default="__nogroup__")
    schema = JSONField(default=dict, blank=True)

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
                        continue
            if sp:
                transaction.savepoint_commit(sp)

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

    def from_geojson(self, geojson_data, from_date='01-01', to_date='12-31',
                     id_field=None, update=False):
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
                f'GeoJSON projection must be in {ACCEPTED_PROJECTIONS}')

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
                from_date=from_date,
                to_date=to_date
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
                        'properties': feature.properties
                        })
            return make_zipfile_bytesio(shape_folder)

    @cached_property
    def layer_projection(self):
        feature = self.features.annotate(srid=ST_SRID(F('geom'))).first()
        return feature.srid

    @cached_property
    def layer_properties(self):
        ''' Return properties of first feature of the layer
        '''
        feature = self.features.first()
        if not feature:
            return {}

        return {
            prop: 'str'
            for prop in feature.properties
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

    def is_projection_allowed(self, projection):
        return projection in ACCEPTED_PROJECTIONS


class Feature(models.Model):
    geom = models.GeometryField()
    identifier = models.CharField(max_length=255,
                                  blank=False,
                                  null=False,
                                  default=uuid.uuid4)
    properties = JSONField()
    layer = models.ForeignKey(Layer,
                              on_delete=models.PROTECT,
                              related_name='features')
    from_date = DateFieldYearLess(help_text="Layer validity period start",
                                  default='01-01')
    to_date = DateFieldYearLess(help_text="Layer validity period end",
                                default='12-31')

    source = models.IntegerField(null=True,
                                 help_text='Internal field used by pgRouting')
    target = models.IntegerField(null=True,
                                 help_text='Internal field used by pgRouting')

    objects = Manager.from_queryset(FeatureQuerySet)()

    def clean_vect_tile_cache(self):
        vtile = VectorTile(self.layer)
        vtile.clean_tiles(self.get_intersected_tiles())

    def get_intersected_tiles(self):
        zoom_range = range(settings.MIN_TILE_ZOOM, settings.MAX_TILE_ZOOM)
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


class LayerRelation(models.Model):
    origin = models.ForeignKey(Layer,
                               on_delete=models.PROTECT,
                               related_name='relations_as_origin')
    destination = models.ForeignKey(Layer,
                                    on_delete=models.PROTECT,
                                    related_name='relations_as_destination')
    schema = JSONField(default=dict, blank=True)


class FeatureRelation(models.Model):
    origin = models.ForeignKey(Feature,
                               on_delete=models.PROTECT,
                               related_name='relations_as_origin')
    destination = models.ForeignKey(Feature,
                                    on_delete=models.PROTECT,
                                    related_name='relations_as_destination')
    properties = JSONField(default=dict, blank=True)
