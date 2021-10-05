CHANGELOG
=========

0.6.3          (2021-10-05)
---------------------------

* Improve performances relations


0.6.2          (2021-10-04)
---------------------------

* Fix email link causing scam-alerts in some email clients


0.6.1          (2021-04-30)
---------------------------

* Improve performances relations


0.6.0          (2021-04-30)
---------------------------

!! WARNING - BREAKING CHANGES !!

* Add constraint extra geom empty / is_valid. Check that your feature extra geometries are not empty or invalid before using this version


0.5.8          (2021-04-30)
---------------------------

* Add format geojson relations


0.5.7          (2020-12-11)
---------------------------

* Include translation files in pypi releases.


0.5.6          (2020-12-11)
---------------------------

* Fix and include translations
* Fix template export mail with hyperlink


0.5.5          (2020-12-10)
---------------------------

* Fix templates not included in setup.py sdist
* Fix save generation export file


0.5.4          (2020-12-01)
---------------------------

* Add endpoint to get all distinct values of any layer property

0.5.3          (2020-11-16)
---------------------------

* Use get_username() to keep compatibility with custom User model
* Revert shape file url generation


0.5.2          (2020-11-06)
---------------------------

* Add functions to export layers in shape / geojson / kml in async mode with a celery worker. User should have email to receive link to download export.


0.5.1          (2020-10-28)
---------------------------

* BugFix on Polygon Vector tiles
* Improve documentation


0.5.0          (2020-10-27)
---------------------------

!! WARNING - BREAKING CHANGES !!

Features with empty geometry will not pass anymore Integrity Error Check
Please, check and fix you geostore_feature table first before making migrations


* Add constraint empty geometries
* Add validation of constraints on geometries


* geostore.routing has been extracted to django-geostore-routing
  * add django-geostore-routing to your project dependencies
  * add geostore_routing to you INSTALLED_APPS instead of geostore.routing
* Add relation property to handle relations directly in feature
* Force geometries 2d

* Improve tile generation


0.4.3          (2020-10-09)
---------------------------

* Fix settings used by renderers


0.4.2          (2020-10-06)
---------------------------

* Fix geometry file labels in feature serializer


0.4.1          (2020-10-02)
---------------------------

* Add KML and GPX renderers


0.4.0          (2020-09-02)
---------------------------

* WARNING Breaking Changes !!
  * to continue to use PGRouting features, please add geostore.routing to INSTALLED_APPS
  * Some changes in routing API response. Now final geometry and full feature segment list are provided by API
  * Configurable tolerance for routing topologies (Default value from 0.0001 to 0.00001)
  * HOSTNAME setting is deprecated. Default request HOST is now used to generate absolute full urls for vector tiles.
You can set TERRA_TILES_HOSTNAMES = [HOSTNAME, ] to avoid this

* Improvements :
  * Officially support django 3.1
  * Set HOSTNAME or TERRA_TILES_HOSTNAMES is not required anymore. Now full absolute urls are prefixed with current host request
  * Installing PGRouting is not required anymore.
  * source / target routing attributes :
    * add indexes
    * Hide by default (editable=False)
  * Using JSONField from django.db.models
  * Updating DjangoModelFactory location


0.3.19         (2020-06-25)
---------------------------

* WARNING : Ordering and Searching in feature properties are disabled for layers without schema.
* OPTIMIZATIONS : Improve API feature by disabling big queries to find layer's properties
* Fix duplicated index

0.3.18         (2020-06-24)
---------------------------

* Improve database indexes

0.3.17         (2020-03-04)
---------------------------

* Factorize Feature Extra Geom serializer to be customized directly in ViewsSet


0.3.16         (2020-01-27)
---------------------------

* Manage relations between layers and features (manual / intersections or distances).
* GeoJson renderer. Now API can render .json or .geojson endpoint (or format=?geojson)
* Partial properties patch. A patch on feature viewset keep properties not sended.
* Add Json value search filter in FeatureViewset


0.3.15         (2019-12-13)
---------------------------

* support django rest framework 3.11


0.3.14         (2019-12-11)
---------------------------

* Officially support django 3.0
* Add possibility to modify, create, update, delete extra geometries
* Add field editable to extra layers


0.3.13         (2019-12-09)
---------------------------

* Order extra geometries by layer


0.3.12         (2019-12-03)
---------------------------

Improves

* Improve documentation

Features

* Ability to define and package extra geometries for features (One to One)


0.3.11    (2019-11-05)
---------------------------

Fixes

* Prevent token group id decoding error


0.3.10         (2019-10-16)
---------------------------

News

* Ability to sort API feature results with property key content

Fixes

* Add missing migration file


0.3.9      (2019-10-15)
----------------------------

* Admin part is removed. Please use your own admin in project.
* DRF yasg is removed. Configure it in your project if required.
* Add authentication management on layers


0.3.8      (2019-10-11)
----------------------------

### Fixes

* Add permission management on FeatureViewset

0.3.7      (2019-10-09)
----------------------------

### Fixes

* Fix tilejson's layer attribution and description parsing

0.3.6      (2019-10-09)
----------------------------

### Fixes

* Fix tilejson when Layer has no Feature
* Fix deprecation warning : "ST_Line_Substring signature was deprecated in 2.1.0. Please use ST_LineSubstring"
* Fix tile generation when no feature is present in the layer
* Fix permission management of layers

0.3.5      (2019-10-03)
-----------------------

### News

* Add a method to get json schema property type by its name

### Fixes

* Fix bug with shapefile export on geometry defined layer.
* Fix group's tiles URLs in tilejson
* Fix tilejson when Layer has no Feature
* Return a tilejson even if it has no feature


0.3.4      (2019-09-26)
-----------------------

### Fixes

* integrate test/factories in packaging


0.3.3      (2019-09-25)
-----------------------

### Breaking Changes with front

* key to access tilejson is changed from 'layer_tilejson' and 'group_tilejson' to 'tilejson' in both cases.

### Fix

* Fix migration file that prevent old terracommon app migration


0.3.2      (2019-09-24)
-----------------------

### Fix

* Fix migration file that prevent old terracommon app migration


0.3.1      (2019-09-11)
-----------------------

### Breaking Changes

* App name move from terra to geostore. Structure is the same, so backup and restore your data


0.3.0      (2019-09-09)
-----------------------

First public tag

* Terra app extracted from terracommon.terra
