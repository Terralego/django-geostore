from django.contrib.gis.db.models import Extent
from django.core.management.base import BaseCommand
from django.db import transaction
from mercantile import tiles

from geostore.models import Layer
from geostore.tiles.helpers import VectorTile


class Command(BaseCommand):
    help = 'Generate tiles cache of all layers'

    @transaction.atomic()
    def handle(self, *args, **options):
        for layer in Layer.objects.all():
            if options['verbosity'] >= 1:
                self.stdout.write(f'Generating {layer.name} tiles cache')
            bbox = layer.features.aggregate(bbox=Extent('geom'))['bbox']
            if bbox:
                vtile = VectorTile(layer)
                zoom_range = range(
                    layer.layer_settings_with_default('tiles', 'minzoom'),
                    layer.layer_settings_with_default('tiles', 'maxzoom') + 1
                )

                for tile in tiles(*bbox, zoom_range):
                    vtile.get_tile(
                        tile.x, tile.y, tile.z
                    )
