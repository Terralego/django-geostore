=========
CHANGELOG
=========

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
