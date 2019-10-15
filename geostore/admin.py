from django.contrib.auth.models import Permission
from django.contrib.gis import admin

from . import models


class LayerAdmin(admin.ModelAdmin):
    list_display = ('pk', 'name', 'geom_type', 'layer_groups')
    list_filter = ('geom_type', 'layer_groups')


class LayerGroupAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    list_filter = ('slug', )


class FeatureAdmin(admin.OSMGeoAdmin):
    list_display = ('pk', 'identifier', 'layer', 'source', 'target')
    list_filter = ('layer', )


admin.site.register(models.FeatureRelation)
admin.site.register(Permission)
