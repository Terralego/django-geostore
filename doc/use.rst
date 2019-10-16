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
  feature = Feature.objects.create(layer=layer,
                                   geom=GEOSGeometry("POINT(0 0)")

  # ok
  feature = Feature.objects.create(layer=layer,
                                   geom=GEOSGeometry("LINESTRING((0 0), (1 1))")
  # ok too

With validation
---------------

.. code-block:: python

  from geostore.models import Layer, Feature
  from geostore import GeometryTypes
  from django.contrib.geos.geometries import GEOSGeometry

  layer = Layer.objects.create(name='Mushroom spot 3',
                               geom_type=GeometryTypes.Point)
  feature = Feature.objects.create(layer=layer,
                                   geom=GEOSGeometry("POINT(0 0)")

  # ok
  feature = Feature.objects.create(layer=layer,
                                   geom=GEOSGeometry("LINESTRING((0 0), (1 1))")
  # validation error !


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
  feature = Feature.objects.create(layer=layer,
                                   geom=GEOSGeometry("POINT(0 0)")
  # Validation Error ! name and age are required

  feature = Feature.objects.create(layer=layer,
                                   geom=GEOSGeometry("POINT(0 0)",
                                   properties={
                                     "name": "Arthur",
                                   })
  # Validation Error ! age is required

  feature = Feature.objects.create(layer=layer,
                                   geom=GEOSGeometry("POINT(0 0)",
                                   properties={
                                     "name": "Arthur",
                                     "age": "ten",
                                   })
  # Validation Error ! age should be integer

  feature = Feature.objects.create(layer=layer,
                                   geom=GEOSGeometry("POINT(0 0)",
                                   properties={
                                     "name": "Arthur",
                                     "age": 10
                                   })
  # ok !


Vector tiles
============

geostore provide endpoint to generate and cache MVT based on your data.

You can access these tiles through Layer and LayerGroup features.


On layers
---------


On group of layers
------------------



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
