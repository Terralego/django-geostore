from rest_framework import serializers

from geostore.serializers import LayerSerializer


class ExtendedLayerSerializer(LayerSerializer):
    extended = serializers.SerializerMethodField()

    def get_extended(self):
        return True
