Configuration
=============


In your project :

# settings
::
    # install required apps
    INSTALLED_APPS = [
        ...
        'django.contrib.gis',  # assume contrib.gis is installed
        ...
        'rest_framework',
        'rest_framework_gis',
        'geostore',
        ...
    ]

    # optional overridable settings
    INTERNAL_GEOMETRY_SRID = 4326 (can be changed for another SRID, should not be changed after 1rst migration)

    HOSTNAME = ''
    TERRA_TILES_HOSTNAMES = [HOSTNAME, ]

    SWAGGER_ENABLED = False

    MAX_TILE_ZOOM = 15
    MIN_TILE_ZOOM = 10


# urls
::

    urlpatterns = [
        ...
        path('', include('geostore.urls', namespace='geostore')),
        ...
    ]

You can customize default url and namespace by including geostore.views directly


# ADMIN :

you can disable and / or customize admin


- BACKWARD compatibility

# settings to add :
::

    import os

    #####

    HOSTNAME = os.environ.get('HOSTNAME', '')
    TERRA_TILES_HOSTNAMES = [HOSTNAME, ]
