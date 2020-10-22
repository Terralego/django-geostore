from django.contrib.gis.db.models import BooleanField
from django.contrib.gis.db.models.fields import BaseSpatialField
from django.db.models.lookups import Transform


@BaseSpatialField.register_lookup
class IsEmpty(Transform):
    lookup_name = 'isempty'
    function = 'ST_ISEMPTY'
    output_field = BooleanField()
