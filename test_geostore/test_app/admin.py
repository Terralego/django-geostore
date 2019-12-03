from django.contrib import admin
from django.contrib.gis.admin import OSMGeoAdmin

from geostore.models import Layer, Feature, LayerExtraGeom, FeatureExtraGeom


class LayerExtraGeomInline(admin.TabularInline):
    model = LayerExtraGeom


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    inlines = [LayerExtraGeomInline]


class FeatureExtraGeomInline(admin.TabularInline):
    model = FeatureExtraGeom


@admin.register(Feature)
class FeatureAdmin(OSMGeoAdmin):
    inlines = [FeatureExtraGeomInline]
