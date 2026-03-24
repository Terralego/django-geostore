Vector Tiles
============

Vector tiles are served following the Mapbox Vector Tiles standard, and using the ST_AsMVT Postgis method.

Most of the work is done in the ``geostore.tiles.helpers`` module.

Settings
--------

Vector tiles can be served in many ways, and it generation can be configured. This allow you to manage which data is returned, but also some tunning settings.

The ``Layer`` models has a ``settings`` attribute which is a ``JSONField``.

Here we describe available json keys and its content, then we provide your an example.

metadata
--------

Contains all data metadata that can be added to tile content, it allows you to store it in a
convenient way.

attribution
^^^^^^^^^^^
**Default: None**

Attribution of the layer's data. Must be a dict like this:
::

{'name': 'OSM contributors', href='http://openstreetmap.org'}

licence
^^^^^^^
**Default: None**

String containing the layer's data licence. i.e.: ODbL, CC-BY, Public Domain, …

description
^^^^^^^^^^^
**Default: None**

Text that describe the data.

tiles
-----

minzoom
^^^^^^^
**Default: 0**

Min zoom when the layer is served in tiles. Must be higher or equal to ``MIN_ZOOM`` setting.

maxzoom
^^^^^^^
**Default: 22**

Max zoom when the layer is served in tiles. Must be lower or equal to ``MAX_ZOOM`` setting.

pixel_buffer
^^^^^^^^^^^^
**Default: 4**

Buffer size around a tile, to match more features and clip features at a larger size than the tile.

Mostly, the default value is enough, but sometimes, depending of the display style (width border of lines or polygons),
you will need to increase this value.

features_filter
^^^^^^^^^^^^^^^
**Default: None**

Filter the features queryset, by this value. Could be used to not return all features of your layers on the tiles.

The complete object is passed to a ``filter(properties__contains)`` method

properties_filter
^^^^^^^^^^^^^^^^^
**Default: None**

List of allowed properties in tiles. This must be a list of properties that will be the only one present in vector tiles.
If set to ``None``, all properties will be returned, else only properties present in the list will be returned.

features_limit
^^^^^^^^^^^^^^
**Default: 10000**

Maximal number of features in a tile. Used to prevent tiles to have too much data, since MVT standard tells a tile must not be high than 500ko.

Example
^^^^^^^

::

  {
        'metadata': {
            'attribution': {'name': 'OSM contributors', href='http://openstreetmap.org'}
            'licence': 'ODbL,
            'description': "Good Licence",
        },
        # Tilesets attributes
        'tiles': {
            'minzoom': 10,
            'maxzoom': 14,
            'pixel_buffer': 4,
            'features_filter': 500,
            'properties_filter': ['my_property', ],
            'features_limit': 10000,
        }
  }
