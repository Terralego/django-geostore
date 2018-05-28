import factory

from django.contrib.gis.geos.geometry import GEOSGeometry

from terracommon.terra.models import Feature, Layer, TerraUser


class TerraUserFactory(factory.DjangoModelFactory):
    class Meta:
        model = TerraUser
    
    email = 'foo@bar.com'
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)


class LayerFactory(factory.DjangoModelFactory):
    class Meta:
        model = Layer

    @factory.post_generation
    def add_features(self, create, features, **kwargs):
        for feature in features:
            FeatureFactory(layer=self, **feature)


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
