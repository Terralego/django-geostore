import json
import logging
import uuid
from itertools import islice

from django.contrib.auth.models import Group
from django.contrib.gis.db import models
from django.contrib.gis.db.models.aggregates import Extent
from django.contrib.gis.db.models.functions import Transform
from django.contrib.gis.geos import GEOSGeometry, WKBWriter
from django.contrib.gis.measure import D

from .import_export.exports import LayerExportMixin
from .import_export.imports import LayerImportMixin

try:
    from django.db.models import JSONField
except ImportError:  # TODO Remove when dropping Django releases < 3.1
    from django.contrib.postgres.fields import JSONField
from django.contrib.postgres.indexes import GistIndex, GinIndex
from django.db import connection, transaction
from django.db.models import Manager
from django.utils.functional import cached_property
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from . import settings as app_settings
from .db.managers import FeatureQuerySet
from .db.mixins import BaseUpdatableModel, LayerBasedModelMixin
from .routing.mixins import PgRoutingMixin, UpdateRoutingMixin

from .tiles.funcs import HausdorffDistance
from .validators import (validate_geom_type, validate_json_schema,
                         validate_json_schema_data)

logger = logging.getLogger(__name__)


class Layer(LayerBasedModelMixin, LayerImportMixin, LayerExportMixin, UpdateRoutingMixin):
    name = models.CharField(max_length=256, unique=True, default=uuid.uuid4, verbose_name=_("Name"))
    schema = JSONField(default=dict, blank=True, validators=[validate_json_schema], verbose_name=_("Schema"))
    authorized_groups = models.ManyToManyField(Group, blank=True, related_name='authorized_layers',
                                               verbose_name=_("Authorized groups"))

    @transaction.atomic
    def update_geometries(self, features):
        modified = self.features.none()
        for new_feature in features:
            geometry = GEOSGeometry(json.dumps(new_feature['geometry']))
            nearest_feature = (
                self.features
                    .filter(geom__bboverlaps=geometry)  # Bounding Box Overlap
                    .annotate(hausdorff=HausdorffDistance('geom',
                                                          geometry))
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
            # noinspection SqlResolve
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

    def get_extent(self, srid=3857):
        return self.features.annotate(
            geom_transformed=Transform('geom', srid)
        ).aggregate(
            extent=Extent('geom_transformed')
        )

    def get_property_values(self, property_to_list):
        property_field = f'properties__{property_to_list}'

        return (
            self.features.order_by(property_field)
            .values_list(property_field, flat='true')
            .distinct(property_field)
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
    name = models.CharField(max_length=256,
                            unique=True,
                            verbose_name=_("Name"))
    slug = models.SlugField(unique=True)
    layers = models.ManyToManyField(Layer,
                                    related_name='layer_groups',
                                    verbose_name=_("Layers"))

    def save(self, **kwargs):
        if self.pk is None:
            self.slug = slugify(self.name)
        super().save(**kwargs)


class Feature(BaseUpdatableModel, PgRoutingMixin):
    geom = models.GeometryField(srid=app_settings.INTERNAL_GEOMETRY_SRID)
    identifier = models.CharField(max_length=255,
                                  blank=False,
                                  null=False,
                                  default=uuid.uuid4,
                                  verbose_name=_("Identifier"))
    properties = JSONField(default=dict,
                           blank=True,
                           verbose_name=_("Properties"))
    layer = models.ForeignKey(Layer,
                              on_delete=models.PROTECT,
                              related_name='features',
                              db_index=False,
                              verbose_name=_("Layer"))

    objects = Manager.from_queryset(FeatureQuerySet)()

    def save(self, *args, **kwargs):
        if self.geom.hasz:
            self.geom = GEOSGeometry(WKBWriter().write(self.geom))
        super(Feature, self).save(*args, **kwargs)

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
            # cache this query because it is evaluated multiple times, this avoids re-executing it as it is costly
            id_list = list(qs.values_list("id", flat=True))
            # find relation to delete (in stored relation but not in qs result)
            to_delete = self.relations_as_origin.filter(relation=rel).exclude(destination_id__in=id_list)

            to_delete.delete()

            # find relation to add (not in stored relation but in qs
            qs = Feature.objects.filter(id__in=id_list).exclude(pk__in=self.relations_as_origin.filter(relation=rel)
                                                                .values_list('destination_id', flat=True))
            # batch creation
            batch_size = 100
            objs = (FeatureRelation(origin=self, destination=feature_rel, relation=rel) for feature_rel in qs.all())
            while True:
                batch = list(islice(objs, batch_size))
                if not batch:
                    break
                FeatureRelation.objects.bulk_create(batch, batch_size)

    @cached_property
    def relations(self):
        return {
            slugify(relation.name): self.relations_as_origin.filter(relation=relation)
            for relation in self.layer.relations_as_origin.all()
        }

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
            # geometry should not be empty
            models.CheckConstraint(check=models.Q(geom__isempty=False), name='geom_is_empty')
        ]


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


class FeatureRelation(models.Model):
    origin = models.ForeignKey(Feature,
                               on_delete=models.CASCADE,
                               related_name='relations_as_origin',
                               verbose_name=_("Origin"))
    destination = models.ForeignKey(Feature,
                                    on_delete=models.CASCADE,
                                    related_name='relations_as_destination',
                                    verbose_name=_("Destination"))
    relation = models.ForeignKey(LayerRelation,
                                 on_delete=models.CASCADE,
                                 related_name='related_features',
                                 verbose_name=_("Relation"))
    properties = JSONField(default=dict,
                           blank=True,
                           verbose_name=_("Properties"))

    class Meta:
        ordering = ['id']


class LayerExtraGeom(LayerBasedModelMixin):
    layer = models.ForeignKey(Layer,
                              on_delete=models.CASCADE,
                              related_name='extra_geometries',
                              verbose_name=_("Layer"))
    order = models.PositiveSmallIntegerField(default=0,
                                             verbose_name=_("Order"))
    slug = models.SlugField(editable=False)
    title = models.CharField(max_length=250,
                             verbose_name=_("Title"))
    editable = models.BooleanField(default=True,
                                   verbose_name=_("Editable"))

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
    feature = models.ForeignKey(Feature,
                                on_delete=models.CASCADE,
                                related_name='extra_geometries',
                                verbose_name=_("Feature"))
    layer_extra_geom = models.ForeignKey(LayerExtraGeom,
                                         on_delete=models.CASCADE,
                                         related_name='features',
                                         verbose_name=_("Feature"))
    geom = models.GeometryField(srid=app_settings.INTERNAL_GEOMETRY_SRID,
                                spatial_index=False)
    properties = JSONField(default=dict,
                           blank=True,
                           verbose_name=_("Properties"))
    identifier = models.UUIDField(blank=True,
                                  null=True,
                                  editable=False,
                                  default=uuid.uuid4,
                                  verbose_name=_("Identifier"))

    class Meta:
        unique_together = (
            ('feature', 'layer_extra_geom'),
        )
        indexes = [
            models.Index(fields=['layer_extra_geom', 'identifier']),
            GistIndex(name='feg_geom_gist_index', fields=['layer_extra_geom', 'geom']),
            GinIndex(name='feg_properties_gin_index', fields=['properties']),
        ]
        constraints = [
            # geometry should be valid
            models.CheckConstraint(check=models.Q(geom__isvalid=True), name='geom_extra_is_valid'),
            # geometry should not be empty
            models.CheckConstraint(check=models.Q(geom__isempty=False), name='geom_extra_is_empty')
        ]
