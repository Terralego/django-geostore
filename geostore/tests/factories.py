import factory
from django.contrib.auth import get_user_model
from django.contrib.gis.geos.geometry import GEOSGeometry

from geostore.models import Feature, Layer


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


UserModel = get_user_model()


class UserFactory(factory.DjangoModelFactory):

    class Meta:
        model = UserModel

    username = factory.Faker('email')
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        kwargs.update({'password': kwargs.get('password', '123456')})
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)
