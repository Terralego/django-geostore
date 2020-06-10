from django.test import TestCase, override_settings

from geostore.settings import app_settings


class SettingsTestCase(TestCase):
    def test_compatibility_with_override_settings(self):
        """
        is bound at import time:
            from geostore.settings import app_settings
        setting_changed signal hook must ensure bound instance
        is refreshed.
        """
        custom_setting = [
            'http://a.tiles.local',
            'http://b.tiles.local',
            'http://c.tiles.local'
        ]
        self.assertIsNone(app_settings.TERRA_TILES_HOSTNAMES, "Checking a known default should be None")

        with override_settings(GEOSTORE={'TERRA_TILES_HOSTNAMES': custom_setting}):
            self.assertListEqual(app_settings.TERRA_TILES_HOSTNAMES,
                                 custom_setting)

        self.assertIsNone(app_settings.TERRA_TILES_HOSTNAMES, "Checking a known default should be None")

        with override_settings(TERRA_TILES_HOSTNAMES=custom_setting):
            self.assertListEqual(app_settings.TERRA_TILES_HOSTNAMES,
                                 custom_setting)
