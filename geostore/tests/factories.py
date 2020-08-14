import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.gis.geos.geometry import GEOSGeometry

from geostore import GeometryTypes
from geostore.models import Feature, Layer


def _get_perm(perm_name):
    """
    Returns permission instance with given name.
    Permission name is a string like 'auth.add_user'.
    """
    app_label, codename = perm_name.split('.')
    return Permission.objects.get(
        content_type__app_label=app_label, codename=codename)


class LayerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Layer

    @factory.post_generation
    def add_features(self, create, features, **kwargs):
        if not features:
            return

        for feature in range(features):
            FeatureFactory(layer=self)


class LayerSchemaFactory(factory.django.DjangoModelFactory):
    geom_type = GeometryTypes.Point
    schema = {
        "type": "object",
        "required": ["name", ],
        "properties": {
            "name": {
                'type': "string",
            },
            "age": {
                'type': "integer",
                "title": "Age",
            },
            "country": {
                'type': "string",
                "title": "Country"
            },
        }
    }

    class Meta:
        model = Layer


class FeatureFactory(factory.django.DjangoModelFactory):
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


class UserFactory(factory.django.DjangoModelFactory):

    class Meta:
        model = UserModel

    username = factory.Faker('email')
    is_active = True

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        kwargs.update({'password': kwargs.get('password', '123456')})
        manager = cls._get_manager(model_class)
        return manager.create_user(*args, **kwargs)

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):
        if create and extracted:
            # We have a saved object and a list of permission names
            self.user_permissions.add(*[_get_perm(pn) for pn in extracted])
