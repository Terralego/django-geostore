|Build Status| |Maintainability| |codecov|

django-geostore
===============

Geographic data store to handle vector data.

* Store your geographic data in layers
* Define and validate geographic type by layer
* Define and validate properties with json schema validation
* Use provided API to manage data (list / creation / update / deletion /
* Generate and serve JSON, Shape files, GeoJSON and Vector Tiles (mapbox protobuf) directly from PostGIS query ST_ASMVT

.. toctree::

   installation
   configuration
   use
   vectortiles
   routing
   tilesgroupaccess

.. |Build Status| image:: https://travis-ci.org/Terralego/django-geostore.svg?branch=master
   :target: https://travis-ci.org/Terralego//django-geostore
.. |Maintainability| image:: https://api.codeclimate.com/v1/badges/b6119d8175fa6f5f5949/maintainability
   :target: https://codeclimate.com/github/Terralego/django-geostore/maintainability
.. |codecov| image:: https://codecov.io/gh/Terralego/django-geostore/branch/master/graph/badge.svg
  :target: https://codecov.io/gh/Terralego/django-geostore
