from geostore.tiles.helpers import guess_minzoom, guess_maxzoom


def zoom_update(func):
    def wrapper(*args, **kargs):
        layer = args[0]
        response = func(*args, **kargs)

        try:
            minzoom = layer.layer_settings('tiles', 'minzoom')
        except KeyError:
            minzoom = guess_minzoom(layer)
            layer.set_layer_settings('tiles', 'minzoom', minzoom)
            layer.save(update_fields=["settings"])

        try:
            layer.layer_settings('tiles', 'maxzoom')
        except KeyError:
            maxzoom = max(guess_maxzoom(layer), minzoom)
            layer.set_layer_settings('tiles', 'maxzoom', maxzoom)
            layer.save(update_fields=["settings"])

        return response
    return wrapper
