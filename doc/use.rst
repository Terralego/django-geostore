###########
QUICK START
###########

*************
Manage layers
*************

The simplest way to create a geographic data layer :

.. code-block:: python

  from geostore import GeometryTypes
  from geostore.models import Layer

  layer = Layer.objects.create(name='Mushroom spot',
                               geom_type=GeometryTypes.Point)


Geometry type validation
========================

Layer support these geometry types :

Supported types
---------------

geostore.GeometryTypes

GeometryCollection = 7
LineString = 1
MultiLineString = 5
MultiPoint = 4
MultiPolygon = 6
Point = 0
Polygon = 3

Define a geometry type to layer to force feature geometry validation.

Without validation
-------------------

.. code-block:: python

  from geostore.models import Layer, Feature
  from geostore import GeometryTypes
  from django.contrib.geos.geometries import GEOSGeometry

  layer = Layer.objects.create(name='Mushroom spot 2')
  feature = Feature(layer=layer,
                    geom=GEOSGeometry("POINT(0 0)")
  feature.clean()  # ok

  feature = Feature(layer=layer,
                    geom=GEOSGeometry("LINESTRING((0 0), (1 1))")

  feature.clean()  # ok too

With validation
---------------

.. code-block:: python

  from geostore.models import Layer, Feature
  from geostore import GeometryTypes
  from django.contrib.geos.geometries import GEOSGeometry

  layer = Layer.objects.create(name='Mushroom spot 3',
                               geom_type=GeometryTypes.Point)
  feature = Feature(layer=layer,
                    geom=GEOSGeometry("POINT(0 0)")

  feature.clean()  # ok

  feature = Feature(layer=layer,
                    geom=GEOSGeometry("LINESTRING((0 0), (1 1))")
  feature.clean()  # validation error !


JSON schema definition / validation
===================================

You can use json schema definition to describe your data content, and improve feature properties validation.

https://json-schema.org/
https://rjsf-team.github.io/react-jsonschema-form/


.. code-block:: python

  from geostore.models import Layer, Feature
  from geostore import GeometryTypes
  from django.contrib.geos.geometries import GEOSGeometry

  layer = Layer.objects.create(name='Mushroom spot 4',
                               geom_type=GeometryTypes.Point,
                               schema={
                                 "required": ["name", "age"],
                                 "properties": {
                                   "name": {
                                     "type": "string",
                                     "title": "Name"
                                   },
                                   "age": {
                                     "type": "integer",
                                     "title": "Age"
                                   }
                                 }
                               })
  feature = Feature(layer=layer,
                    geom=GEOSGeometry("POINT(0 0)")
  feature.clean()  # Validation Error ! name and age are required

  feature = Feature(layer=layer,
                    geom=GEOSGeometry("POINT(0 0)",
                    properties={
                        "name": "Arthur",
                    })
  feature.clean()  # Validation Error ! age is required

  feature = Feature(layer=layer,
                    geom=GEOSGeometry("POINT(0 0)",
                    properties={
                      "name": "Arthur",
                      "age": "ten",
                    })
  feature.clean()  # Validation Error ! age should be integer

  feature = Feature(layer=layer,
                    geom=GEOSGeometry("POINT(0 0)",
                    properties={
                      "name": "Arthur",
                      "age": 10
                    })
  feature.clean()  # ok !


Vector tiles
============

geostore provide endpoint to generate and cache MVT based on your data.

You can access these tiles through Layer and LayerGroup features.


On layers
---------


On group of layers
------------------


Relations
=========

* You can define relations between layers (and features)

.. warning::
    Compute relations need celery project and worker configured in your project.
    Run at least 1 worker.
    You need to fix settings explicitly to enable asynchronous tasks.
    GEOSTORE_RELATION_CELERY_ASYNC = True

Manual relation
---------------

No automatic links between features. You need to create yourself FeatureRelation between Features.

Automatic relations
-------------------

If celery project / worker is available, and GEOSTORE_RELATION_CELERY_ASYNC settings set to True,
each layer relation creation / or feature creation / update will launch async task to update relation between associated features.

Data import
===========

ShapeFile
---------

GeoJSON
-------


Data export
===========

API endpoints
=============
