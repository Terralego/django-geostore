Routing
=======

Django-Geostore integrate a way to use your LineString layer as a routing one. It uses pgRouting as backend.


Prerequisites
-------------

 * pgRouting>=2.5

Settings
--------

pgRouting needs to update a table that contains all linestring connections, to do you need to execute
the management command we made:

::
  ./manage.py update_topology -pk <layer_pk>

You must provide the pk of the layer you want to use.


Usage
-----

The layer viewset has a route that provide a endpoint to get a routing result between two or more points.

``^layer/<pk>/route``

Arguments
^^^^^^^^^

First attribute needed, and mandatory, is ``geom``, it must contrains a LineString from start to endpoint, passing through all
the waypoints. Geostore will create a path passing on the intersection the closest of those point, in the order you provided it.

It can also be provided a ``callbackid``, that is used to identify the request. It can be usefull in async environment. The ``callbackid``
is provided «as is» in the response.

Query content can provided in a POST or a GET request.

An example of response:

:: json

    {
        'request': {
            'callbackid': "my_callback",
            'geom': {
                "type": "LineString",
                "coordinates": [
                [
                    10.8984375,
                    52.1874047455997
                ],
                [
                    1.58203125,
                    46.042735653846506
                ]
                ]
            },
        },
        'geom': {
            "type": "LineString",
            "coordinates": [
            [
                1.6259765625,
                45.767522962149876
            ],
            [
                5.2294921875,
                46.558860303117164
            ],
            [
                10.986328125,
                52.10650519075632
            ]
            ]
        },
    }

