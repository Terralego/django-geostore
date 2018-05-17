import json
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.gis.db import models
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.postgres.fields import JSONField
from django.contrib.gis.geos.point import Point

from django.core.serializers import serialize
from django.db.models import Manager
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .fields import DateFieldYearLess
from .managers import FeatureQuerySet, TerraUserManager


class Layer(models.Model):
    name = models.CharField(max_length=256)
    group = models.CharField(max_length=255, default="__nogroup__")
    schema = JSONField(default=dict, blank=True)

    def from_csv_dictreader(self, reader, pk_properties, init=False, chunk_size=1000):
        """Import (create or update) features from csv.DictReader object
        :param reader: csv.DictReader object
        :param pk_properties: keys of row that is used to identify unicity
        :param init: permit to speed up import if there is only new Feature's (no updates)
        :param chunk_size: only used if init=True, control the size of bulk_create
        """
        if init:
            rl = list(reader)
            for chunk in [rl[i:i+chunk_size] for i in range(0, len(rl), chunk_size)]:
                entries = [
                    Feature(
                        geom=Point(),
                        properties=row,
                        layer=self,
                    )
                    for row in chunk
                ]
                Feature.objects.bulk_create(entries)
        else:
            for row in reader:
                Feature.objects.update_or_create(
                    defaults={
                        'geom': Point(),
                        'properties': row,
                        'layer': self,
                    },
                    layer=self,
                    **{f'properties__{p}': row.get(p, '') for p in pk_properties}
                )

    def from_geojson(self, geojson_data, from_date, to_date):
        """
        Import geojson raw data in a layer
        Args:
            geojson_data(str): must be raw text json data
        """
        geojson = json.loads(geojson_data)
        for feature in geojson.get('features', []):
            Feature.objects.create(
                layer=self,
                properties=feature.get('properties', {}),
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


class Feature(models.Model):
    geom = models.GeometryField()
    properties = JSONField()
    layer = models.ForeignKey(Layer,
                              on_delete=models.PROTECT,
                              related_name='features')
    from_date = DateFieldYearLess(help_text="Layer validity period start",
                                  default='01-01')
    to_date = DateFieldYearLess(help_text="Layer validity period end",
                                default='12-31')

    objects = Manager.from_queryset(FeatureQuerySet)()


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


class TerraUser(AbstractBaseUser, PermissionsMixin):
    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = []

    uuid = models.UUIDField(_('unique identifier'),
                            default=uuid.uuid4,
                            editable=False,
                            unique=True)
    email = models.EmailField(_('email address'), blank=True, unique=True)
    properties = JSONField(default=dict, blank=True)
    is_staff = models.BooleanField(
        _('staff status'),
        default=False,
        help_text=_('Designates whether the user '
                    'can log into this admin site.'),
    )
    is_active = models.BooleanField(
        _('active'),
        default=True,
        help_text=_(
            'Designates whether this user should be treated as active. '
            'Unselect this instead of deleting accounts.'
        ),
    )
    date_joined = models.DateTimeField(_('date joined'), default=timezone.now)

    objects = TerraUserManager()
