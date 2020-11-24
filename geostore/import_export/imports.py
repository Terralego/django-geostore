import json
import logging
import uuid

import fiona
from django.contrib.gis.geos import GEOSGeometry, GEOSException
from django.db import transaction
from fiona.transform import transform_geom

from geostore.import_export.helpers import ChunkIterator

from geostore import settings as app_settings
from geostore.tiles.decorators import zoom_update

ACCEPTED_PROJECTIONS = [
    'urn:ogc:def:crs:OGC:1.3:CRS84',
    'EPSG:4326',
]
logger = logging.getLogger(__name__)


class LayerImportMixin:
    def _fiona_shape_projection(self, shapefile):
        """ Return projection in EPSG format or raw Proj format extracted from
            shape
        """
        proj = shapefile.crs
        if proj and (len(proj) == 1 or (len(proj) == 2 and proj.get('no_defs') is True)):
            return proj.get('init')
        else:
            return fiona.crs.to_string(proj)

    def is_projection_allowed(self, projection):
        return projection in ACCEPTED_PROJECTIONS

    @zoom_update
    def from_shapefile(self, zipped_shapefile_file, id_field=None):
        """ Load ShapeFile content provided into a zipped archive.

        zipped_shapefile_file -- a file-like object on the zipped content
        id_field -- the field name used a identifier
        """
        from geostore.models import Feature  # fix circular imports
        with fiona.BytesCollection(zipped_shapefile_file.read()) as shape:
            # Extract source projection and compute if reprojection is required
            projection = self._fiona_shape_projection(shape)
            reproject = projection and not self.is_projection_allowed(projection.upper())

            for feature in shape:
                properties = {}
                for prop, value in feature.get('properties', {}).items():
                    try:
                        properties[prop] = json.loads(value)
                    except (json.JSONDecodeError, TypeError):
                        properties[prop] = value

                geometry = feature.get('geometry')

                if reproject:
                    geometry = transform_geom(
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

    @zoom_update
    def from_geojson(self, geojson_data, id_field=None, update=False):
        """
        Import geojson raw data in a layer
        Args:
            geojson_data(str): must be raw text json data
        """
        from geostore.models import Feature  # fix circular imports
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

    def _initial_import_from_csv(self, chunks, options, operations):
        from geostore.models import Feature  # fix circular imports
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
        from geostore.models import Feature  # fix circular imports
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
            Feature.objects.filter(**filter_kwargs) \
                .update(properties=feature_args["properties"])

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
