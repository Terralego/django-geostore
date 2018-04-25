from django.contrib.gis import admin

from .models import Layer, Feature, FeatureRelation


admin.site.register(Layer)
admin.site.register(Feature, admin.OSMGeoAdmin)
admin.site.register(FeatureRelation)
