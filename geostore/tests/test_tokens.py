from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import RequestFactory, TestCase
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from geostore.models import LayerGroup
from geostore.serializers import GroupSerializer
from geostore.tests.factories import FeatureFactory, LayerFactory, SuperUserFactory, UserFactory
from geostore.tiles.helpers import GeoStoreVectorLayer, VectorTile
from geostore.tiles.mixins import MVTViewMixin
from geostore.tokens import GroupTilesToken, tiles_token_generator

UserModel = get_user_model()


class GroupSerializerTestCase(TestCase):
    def test_group_serializer_tilejson_and_group_tiles(self):
        layer_group = LayerGroup.objects.create(name='Test Group', slug='test-group')
        serializer = GroupSerializer(layer_group)
        data = serializer.data
        self.assertIn('tilejson', data)
        self.assertIn('group_tiles', data)
        self.assertIn('test-group', data['tilejson'])
        self.assertIn('test-group', data['group_tiles'])


class GroupTilesTokenTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        self.layer_group = LayerGroup.objects.create(name='Group 1', slug='group-1')
        self.layer_group.layers.add(self.layer)

        self.group = Group.objects.create(name='Authorized Group')
        self.layer.authorized_groups.add(self.group)

        self.user = UserFactory()
        self.user.groups.add(self.group)

    def test_get_groups_intersect(self):
        token_gen = GroupTilesToken()
        intersect = token_gen.get_groups_intersect(self.user, self.layer_group)
        self.assertIn(self.group, intersect)

    def test_token_idb64_and_decode(self):
        groups = Group.objects.filter(pk=self.group.pk)
        idb64 = tiles_token_generator.token_idb64(groups, self.layer_group)
        decoded_groups, decoded_lg = tiles_token_generator.decode_idb64(idb64)
        self.assertEqual(decoded_lg, self.layer_group)
        self.assertIn(self.group, decoded_groups)

    def test_make_and_check_token(self):
        groups = Group.objects.filter(pk=self.group.pk)
        token = tiles_token_generator.make_token(groups, self.layer_group)
        self.assertTrue(tiles_token_generator.check_token(token, groups, self.layer_group))

    def test_decode_idb64_invalid(self):
        # Missing dash
        bad_idb64 = urlsafe_base64_encode(force_bytes('nodash'))
        groups, lg = tiles_token_generator.decode_idb64(bad_idb64)
        self.assertIsNone(groups)
        self.assertIsNone(lg)

        # Non-existent layergroup pk
        non_existent_idb64 = urlsafe_base64_encode(force_bytes('9999-99999'))
        groups, lg = tiles_token_generator.decode_idb64(non_existent_idb64)
        self.assertIsNone(groups)
        self.assertIsNone(lg)

        # Invalid format (e.g. non-numeric id)
        invalid_idb64 = urlsafe_base64_encode(force_bytes('abc-def'))
        groups, lg = tiles_token_generator.decode_idb64(invalid_idb64)
        self.assertIsNone(groups)
        self.assertIsNone(lg)


class DummyTileView(MVTViewMixin):
    def __init__(self, request):
        self.request = request


class AuthenticatedGroupsMixinTestCase(TestCase):
    def setUp(self):
        self.rf = RequestFactory()
        self.user = UserFactory()
        self.layer = LayerFactory()
        self.layer_group = LayerGroup.objects.create(name='Group 2', slug='group-2')
        self.layer_group.layers.add(self.layer)
        self.group = Group.objects.create(name='AuthGroup')
        self.layer.authorized_groups.add(self.group)

    def test_authenticated_groups_with_valid_token(self):
        groups = Group.objects.filter(pk=self.group.pk)
        idb64 = tiles_token_generator.token_idb64(groups, self.layer_group)
        token = tiles_token_generator.make_token(groups, self.layer_group)

        request = self.rf.get('/', {'idb64': idb64, 'token': token})
        request.user = self.user
        view = DummyTileView(request)
        auth_groups = view.authenticated_groups
        self.assertIn(self.group, auth_groups)

        # is_authorized with matching authorized_groups
        self.assertTrue(view.is_authorized(self.layer))

        # is_authorized with non-matching authorized_groups
        other_group = Group.objects.create(name='Other')
        other_layer = LayerFactory()
        other_layer.authorized_groups.add(other_group)
        self.assertFalse(view.is_authorized(other_layer))

        # tokenized url
        tokenized_url = view.get_tokenized_url('/tiles/pattern/')
        self.assertIn('idb64=', tokenized_url)
        self.assertIn('token=', tokenized_url)

    def test_is_authorized_superuser(self):
        superuser = SuperUserFactory()
        request = self.rf.get('/')
        request.user = superuser
        view = DummyTileView(request)
        self.assertTrue(view.is_authorized(self.layer))

    def test_settings_link(self):
        # Settings with link
        layer = LayerFactory(settings={
            'metadata': {
                'attribution': {
                    'name': 'OSM Contributors',
                    'link': 'https://www.openstreetmap.org',
                }
            }
        })
        rendered_link = MVTViewMixin.settings_link(layer, 'metadata', 'attribution')
        self.assertIn('<a href="https://www.openstreetmap.org"/>OSM Contributors</a>', rendered_link)

        # Settings without link
        layer_no_link = LayerFactory(settings={
            'metadata': {
                'description': 'A simple layer'
            }
        })
        val = MVTViewMixin.settings_link(layer_no_link, 'metadata', 'description')
        self.assertEqual(val, 'A simple layer')


class TilesHelpersTestCase(TestCase):
    def setUp(self):
        self.layer = LayerFactory()
        FeatureFactory(layer=self.layer, properties={'city': 'Paris', 'code': 75})
        FeatureFactory(layer=self.layer, properties={'city': 'Lyon', 'code': 69})

    def test_vector_layer_filters_and_cache_key(self):
        self.layer.set_layer_settings('tiles', 'features_filter', {'city': 'Paris'})
        self.layer.set_layer_settings('tiles', 'properties_filter', ['city'])
        vl = GeoStoreVectorLayer(self.layer)
        qs = vl.get_vector_tile_queryset()
        self.assertEqual(qs.count(), 1)
        fields = vl.get_tile_fields()
        self.assertEqual(fields, ('properties__city', 'identifier'))

        cache_key = vl.get_tile_cache_key(0, 0, 0)
        self.assertTrue(isinstance(cache_key, str))

    def test_vector_layer_get_layer_fields_no_layer_properties(self):
        layer = LayerFactory()
        vl = GeoStoreVectorLayer(layer)
        vl._include_fields = True

        # Emulate a layer object that doesn't have layer_properties
        class LayerWithoutProps:
            def layer_settings_with_default(self, *args):
                return None

        vl.layer = LayerWithoutProps()
        fields = vl.get_layer_fields()
        self.assertEqual(fields, {})

    def test_vector_tile_cache_key_with_filters(self):
        vt = VectorTile(self.layer, cache_key='custom_cache_key')
        vt.features_filter = {'city': 'Paris'}
        vt.properties_filter = ['city', 'code']
        cache_key = vt.get_tile_cache_key(1, 2, 3)
        self.assertTrue(isinstance(cache_key, str))
