###########
QUICK START
###########

*************
Manage layers
*************

.. code-block:: python
  from geostore.models import Layer

  layer = Layer.objects.create(name='Mushroom spot',
                               geom_type=GeometryTypes.Point)


Geometry type validation
========================

Supported types
---------------

.. automodule:: geostore.GeometryTypes


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

https://json-schema.org/
https://rjsf-team.github.io/react-jsonschema-form/

With validation
---------------

Without validation
------------------

Vector tiles
============

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
