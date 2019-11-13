from django.contrib import admin
from geostore.models import Layer, Feature, LayerSchemaProperty, ArrayObjectProperty


class ArrayObjectPropertyAdminInline(admin.TabularInline):
    model = ArrayObjectProperty


class LayerSchemaPropertyAdminInline(admin.TabularInline):
    model = LayerSchemaProperty

from django.contrib.gis.admin import OSMGeoAdmin

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


class LayerSchemaPropertyAdmin(admin.ModelAdmin):
    inlines = [ArrayObjectPropertyAdminInline, ]


@admin.register(Layer)
class LayerAdmin(admin.ModelAdmin):
    inlines = [LayerSchemaPropertyAdminInline]


@admin.register(Feature)
class FeatureAdmin(OSMGeoAdmin):
    inlines = [FeatureExtraGeomInline]


admin.site.register(ArrayObjectProperty)
admin.site.register(LayerSchemaProperty, LayerSchemaPropertyAdmin)
