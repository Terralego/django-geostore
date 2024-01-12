from django.contrib import admin
try:
    from django.contrib.gis.admin import GISModelAdmin
except ImportError:
    from django.contrib.admin import OSMGeoAdmin as GISModelAdmin

from geostore.models import Layer, Feature, LayerExtraGeom, FeatureExtraGeom, LayerRelation


class LayerExtraGeomInline(admin.TabularInline):
    model = LayerExtraGeom


class LayerRelationInline(admin.TabularInline):
    fk_name = 'origin'
    model = LayerRelation
    extra = 0


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    inlines = [LayerExtraGeomInline, LayerRelationInline]


class FeatureExtraGeomInline(admin.TabularInline):
    model = FeatureExtraGeom


@admin.register(Feature)
class FeatureAdmin(GISModelAdmin):
    list_filter = ('layer', )
    inlines = [FeatureExtraGeomInline]
