Configuration
=============


In your project :

Add geostore to your ``INSTALLED_APPS`` :

::

    # install required apps
    INSTALLED_APPS = [
        ...
        'django.contrib.gis',  # assume contrib.gis is installed
        ...
        'rest_framework',
        'rest_framework_gis',
        'geostore',
        #'geostore.routing',  # uncomment to enable routing features. Required PgRouting installed.
        ...
    ]

Settings
********

warning::
  Geostore will change the geojson serializer on app loading.

GEOSTORE_INTERNAL_GEOMETRY_SRID
-------------------------------
**Default: 4326**

It's the installation SRID, it must be set before the first migration and never change after installation,
else you must create your own migrations to change your database SRID.

GEOSTORE_TILE_HOSTNAMES
-----------------------
**Default: []**

It contains the list of base URLs where are served the vector tiles.
Since web browsers limit the number of connections to one domain name, a workaround is to use
many domains to serve vector tiles, so browser will create more tcp connections, and the tiles loading
will be faster.
Don't forget to redirect these domain and accept them in ALLOWED_HOSTS settings.

GEOSTORE_MAX_TILE_ZOOM
----------------------
**Default: 15**

It represent the max authorized zoom, if a tile with a zoom above this setting is requested, geostore will refuse to serve it.


GEOSTORE_MIN_TILE_ZOOM
----------------------
**Default: 10**

Like for ``GEOSTORE_MAX_TILE_ZOOM`` setting, if a tile of a lesser zoom than this setting is requested, backend will refuse to serve it.


(DEPRECATED) INTERNAL_GEOMETRY_SRID
-----------------------------------
**replaced by GEOSTORE_INTERNAL_GEOMETRY_SRID**

(DEPRECATED) HOSTNAME
---------------------
**no replaced. See GEOSTORE_TILE_HOSTNAMES**

(DEPRECATED) TERRA_TILES_HOSTNAMES
----------------------------------
**replaced by GEOSTORE_TILE_HOSTNAMES**


(DEPRECATED) MAX_TILE_ZOOM
--------------------------
**replaced by GEOSTORE_MAX_TILE_ZOOM**


(DEPRECATED) MIN_TILE_ZOOM
--------------------------
**replaced by GEOSTORE_MIN_TILE_ZOOM**


URLs
****

Add to you urls.py file this pattern:

::

    urlpatterns = [
        ...
        path('', include('geostore.urls', namespace='geostore')),
        ...
    ]

You can customize default url and namespace by including geostore.views directly


Admin
-----

you can disable and / or customize admin
