import factory
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.contrib.gis.geos.geometry import GEOSGeometry

from geostore import GeometryTypes
from geostore.models import Feature, Layer, LayerSchemaProperty


def _get_perm(perm_name):
    """
    Returns permission instance with given name.
    Permission name is a string like 'auth.add_user'.
    """
    app_label, codename = perm_name.split('.')
    return Permission.objects.get(
        content_type__app_label=app_label, codename=codename)


class LayerFactory(factory.DjangoModelFactory):
    class Meta:
        model = Layer

    @factory.post_generation
    def add_features(self, create, features, **kwargs):
        if not features:
            return

        for feature in range(features):
            FeatureFactory(layer=self)


class LayerWithSchemaFactory(factory.DjangoModelFactory):
    geom_type = GeometryTypes.Point

    @factory.post_generation
    def create_schmeas_properties(obj, create, extracted, **kwargs):
        LayerSchemaProperty.objects.create(slug="name", required=True, prop_type="string", layer=obj)
        LayerSchemaProperty.objects.create(slug="age", required=False, prop_type="integer", title="Age", layer=obj)
        LayerSchemaProperty.objects.create(slug="country", required=False, prop_type="string", title="Country",
                                           layer=obj)

    class Meta:
        model = Layer


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

    @factory.post_generation
    def permissions(self, create, extracted, **kwargs):
        if create and extracted:
            # We have a saved object and a list of permission names
            self.user_permissions.add(*[_get_perm(pn) for pn in extracted])


class SchemaFactory(factory.DjangoModelFactory):
    slug = factory.Sequence(lambda n: "property%s" % n)
    prop_type = "string"
    layer = factory.SubFactory(Layer)

    class Meta:
        model = LayerSchemaProperty
