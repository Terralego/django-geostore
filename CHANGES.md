CHANGELOG
=========

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
