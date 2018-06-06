from django.contrib.auth.models import Permission
from django.contrib.gis import admin

from .models import Feature, FeatureRelation, Layer

admin.site.register(Layer)
admin.site.register(Feature, admin.OSMGeoAdmin)
admin.site.register(FeatureRelation)
admin.site.register(Permission)
