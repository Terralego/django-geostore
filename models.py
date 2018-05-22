import json
import uuid

from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.contrib.gis.db import models
from django.contrib.gis.geos.geometry import GEOSGeometry
from django.contrib.postgres.fields import JSONField
from django.core.serializers import serialize
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .fields import DateFieldYearLess
from .managers import FeatureManager, TerraUserManager


class Layer(models.Model):
    name = models.CharField(max_length=256)
    schema = JSONField(default=dict, blank=True)

    def from_geojson(self, geojson_data):
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
                geom=GEOSGeometry(json.dumps(feature.get('geometry')))
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

    objects = FeatureManager()

    objects = FeatureManager()


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
