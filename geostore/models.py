import glob
import json
import logging
import os
import uuid
from itertools import islice
from tempfile import TemporaryDirectory

import fiona
import fiona.transform
from django.contrib.auth.models import Group
from django.contrib.gis.db import models
from django.contrib.gis.db.models.aggregates import Extent
from django.contrib.gis.db.models.functions import Transform
from django.contrib.gis.geos import GEOSException, GEOSGeometry
from django.contrib.gis.measure import D
try:
    from django.db.models import JSONField
except ImportError:  # TODO Remove when dropping Django releases < 3.1
    from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GistIndex, GinIndex
from django.core.serializers import serialize
from django.db import connection, transaction
from django.db.models import Manager
from django.db.models.signals import post_save
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _
from fiona.crs import from_epsg

from . import GeometryTypes, settings as app_settings
from .db.managers import FeatureQuerySet
from .db.mixins import BaseUpdatableModel, LayerBasedModelMixin
from .helpers import ChunkIterator, make_zipfile_bytesio
from .routing.db.mixins import PgRoutingMixin
from .routing.decorators import topology_update
from .signals import save_feature, save_layer_relation
from .tiles.decorators import zoom_update
from .tiles.funcs import ST_HausdorffDistance
from .validators import (validate_geom_type, validate_json_schema,
                         validate_json_schema_data)

logger = logging.getLogger(__name__)

ACCEPTED_PROJECTIONS = [
    'urn:ogc:def:crs:OGC:1.3:CRS84',
    'EPSG:4326',
]


class Layer(LayerBasedModelMixin):
    name = models.CharField(max_length=256, unique=True, default=uuid.uuid4)
    schema = JSONField(default=dict, blank=True, validators=[validate_json_schema])
    authorized_groups = models.ManyToManyField(Group, blank=True, related_name='authorized_layers')

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
            Feature.objects.filter(**filter_kwargs)\
                .update(properties=feature_args["properties"])

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

    def is_projection_allowed(self, projection):
        return projection in ACCEPTED_PROJECTIONS

    def get_extent(self, srid=3857):
        return self.features.annotate(
            geom_transformed=Transform('geom', srid)
        ).aggregate(
            extent=Extent('geom_transformed')
        )

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


class Feature(BaseUpdatableModel, PgRoutingMixin):
    geom = models.GeometryField(srid=app_settings.INTERNAL_GEOMETRY_SRID)
    identifier = models.CharField(max_length=255,
                                  blank=False,
                                  null=False,
                                  default=uuid.uuid4)
    properties = JSONField(default=dict, blank=True)
    layer = models.ForeignKey(Layer,
                              on_delete=models.PROTECT,
                              related_name='features',
                              db_index=False)

    objects = Manager.from_queryset(FeatureQuerySet)()

    def get_bounding_box(self):
        return self.geom.extent

    def get_computed_relation_qs(self, relation):
        """ Execute relation operation to get feature queryset """
        qs_empty = Feature.objects.none()

        if relation not in self.layer.relations_as_origin.all():
            # relation should be in layer_relation_as_origins
            return qs_empty

        qs = relation.destination.features.all()
        kwargs = {}
        if relation.relation_type == 'intersects':
            kwargs.update({
                'geom__intersects': self.geom,
            })
        elif relation.relation_type == 'distance':
            kwargs.update({
                'geom__distance_lte': (self.geom,
                                       D(m=relation.settings.get('distance')),
                                       'spheroid'),
            })

        qs = qs.filter(**kwargs) if kwargs else qs
        qs = qs.exclude(**relation.exclude) if relation.exclude else qs

        return qs

    def get_stored_relation_qs(self, layer_relation):
        destination_ids = self.relations_as_origin.filter(relation=layer_relation) \
            .values_list('destination_id', flat=True)
        return Feature.objects.filter(pk__in=destination_ids)

    def sync_relations(self, layer_relation=None):
        """ replace feature relations for automatic layer relations """
        logger.info("Feature relation synchronisation")
        layer_relations = self.layer.relations_as_origin.exclude(relation_type__isnull=True)
        layer_relations = layer_relations.filter(pk__in=[layer_relation]) if layer_relation else layer_relations
        for rel in layer_relations:
            logger.info(f"relation {rel}")
            qs = self.get_computed_relation_qs(rel)
            # find relation to delete (in stored relation but not in qs result)
            to_delete = self.relations_as_origin.filter(relation=rel).exclude(destination_id__in=qs)

            logger.info(f"{to_delete.count()} element(s) to delete")

            to_delete.delete()

            # find relation to add (not in stored relation but in qs
            qs = qs.exclude(pk__in=self.relations_as_origin.filter(relation=rel)
                                                           .values_list('destination_id', flat=True))
            logger.info(f"{len(qs)} element(s) to add")
            # batch creation
            batch_size = 100
            objs = (FeatureRelation(origin=self, destination=feature_rel, relation=rel) for feature_rel in qs.all())
            while True:
                batch = list(islice(objs, batch_size))
                if not batch:
                    break
                FeatureRelation.objects.bulk_create(batch, batch_size)

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
            models.Index(fields=['layer', 'identifier']),
            models.Index(fields=['id', 'layer', ]),
            models.Index(fields=['source', 'layer', ]),
            models.Index(fields=['target', 'layer', ]),
            models.Index(fields=['source', 'target', 'layer']),
            GistIndex(fields=['layer', 'geom']),
            GinIndex(name='properties_gin_index', fields=['properties']),
        ]
        constraints = [
            # geometry should be valid
            models.CheckConstraint(check=models.Q(geom__isvalid=True), name='geom_is_valid'),
        ]


post_save.connect(save_feature, sender=Feature)


class LayerRelation(models.Model):
    RELATION_TYPES = (
        (None, 'Manual'),
        ('intersects', 'Intersects'),
        ('distance', 'Distance'),
    )
    name = models.CharField(max_length=250)
    slug = models.SlugField(editable=False)
    origin = models.ForeignKey(Layer,
                               on_delete=models.PROTECT,
                               related_name='relations_as_origin')
    destination = models.ForeignKey(Layer,
                                    on_delete=models.PROTECT,
                                    related_name='relations_as_destination')
    relation_type = models.CharField(choices=RELATION_TYPES, blank=True, max_length=25, default=RELATION_TYPES[0])
    settings = JSONField(default=dict, blank=True)
    exclude = JSONField(default=dict, blank=True,
                        help_text=_("qs exclude (ex: {\"pk__in\": [...], \"identifier__in\":[...]}"))

    def save(self, *args, **kwargs):
        self.clean()
        self.slug = slugify(f'{self.origin_id}-{self.name}')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['id']
        unique_together = (
            ('name', 'origin'),
        )


post_save.connect(save_layer_relation, sender=LayerRelation)


class FeatureRelation(models.Model):
    origin = models.ForeignKey(Feature,
                               on_delete=models.CASCADE,
                               related_name='relations_as_origin')
    destination = models.ForeignKey(Feature,
                                    on_delete=models.CASCADE,
                                    related_name='relations_as_destination')
    relation = models.ForeignKey(LayerRelation,
                                 on_delete=models.CASCADE,
                                 related_name='related_features')
    properties = JSONField(default=dict, blank=True)

    class Meta:
        ordering = ['id']


class LayerExtraGeom(LayerBasedModelMixin):
    layer = models.ForeignKey(Layer, on_delete=models.CASCADE, related_name='extra_geometries')
    order = models.PositiveSmallIntegerField(default=0)
    slug = models.SlugField(editable=False)
    title = models.CharField(max_length=250)
    editable = models.BooleanField(default=True)

    @cached_property
    def name(self):
        return f"{slugify(self.layer.name)}-{self.slug}"

    def save(self, **kwargs):
        if self.pk is None:
            self.slug = slugify(self.title)
        super().save(**kwargs)

    def __str__(self):
        return f"{self.title} ({self.layer})"

    class Meta:
        unique_together = (
            ('layer', 'slug'),
            ('layer', 'title'),
        )
        ordering = (
            'layer', 'order'
        )


class FeatureExtraGeom(BaseUpdatableModel):
    feature = models.ForeignKey(Feature, on_delete=models.CASCADE, related_name='extra_geometries')
    layer_extra_geom = models.ForeignKey(LayerExtraGeom, on_delete=models.CASCADE, related_name='features')
    geom = models.GeometryField(srid=app_settings.INTERNAL_GEOMETRY_SRID, spatial_index=False)
    properties = JSONField(default=dict, blank=True)
    identifier = models.UUIDField(blank=True, null=True, editable=False, default=uuid.uuid4)

    class Meta:
        unique_together = (
            ('feature', 'layer_extra_geom'),
        )
        indexes = [
            models.Index(fields=['layer_extra_geom', 'identifier']),
            GistIndex(name='feg_geom_gist_index', fields=['layer_extra_geom', 'geom']),
            GinIndex(name='feg_properties_gin_index', fields=['properties']),
        ]
