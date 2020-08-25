from copy import deepcopy
from functools import reduce

from deepmerge import always_merger
try:
    from django.db.models import JSONField
except ImportError:  # TODO Remove when dropping Django releases < 3.1
    from django.contrib.postgres.fields import JSONField
from django.db import models
from django.utils.functional import cached_property

from geostore import GeometryTypes


class BaseUpdatableModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class LayerBasedModelMixin(BaseUpdatableModel):
    # Settings schema
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
    geom_type = models.IntegerField(choices=GeometryTypes.choices(), null=True)

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
        """
        Return the geometry type of the layer using the first feature in
        the layer if the layer have no geom_type or the geom_type of the layer
        """
        if self.geom_type is None:
            feature = self.features.first()
            if feature:
                return feature.geom.geom_typeid
        return self.geom_type

    @cached_property
    def settings_with_default(self):
        return always_merger.merge(deepcopy(self.SETTINGS_DEFAULT), self.settings)

    def layer_settings(self, *json_path):
        """ Return the nested value of settings at path json_path.
            Raise an KeyError if not defined.
        """
        # Dives into settings using args
        return reduce(
            lambda a, v: a[v],  # Let raise KeyError on missing key
            json_path,
            self.settings) if self.settings is not None else None

    def layer_settings_with_default(self, *json_path):
        """ Return the nested value of settings with SETTINGS_DEFAULT as
            fallback at path json_path.
            Raise an KeyError if not defined.
        """
        # Dives into settings using args
        return reduce(
            lambda a, v: a[v],  # Let raise KeyError on missing key
            json_path,
            self.settings_with_default)

    def set_layer_settings(self, *json_path_value):
        """ Set last parameter as value at the path place into settings """

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

    class Meta:
        abstract = True
