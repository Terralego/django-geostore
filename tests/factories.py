import factory
from django.contrib.gis.geos.geometry import GEOSGeometry

from terracommon.terra.models import Feature, Layer


class LayerFactory(factory.DjangoModelFactory):
    class Meta:
        model = Layer

    @factory.post_generation
    def add_features(self, create, features, **kwargs):
        if not features:
            return

        for feature in range(features):
            FeatureFactory(layer=self)


class FeatureFactory(factory.DjangoModelFactory):
    layer = factory.SubFactory(LayerFactory)
    geom = GEOSGeometry('''{
        "type": "Point",
        "coordinates": [
          2.4609375,
          45.583289756006316
        ]
      }''')
    properties = {}

    class Meta:
        model = Feature
