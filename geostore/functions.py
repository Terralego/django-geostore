from django.contrib.gis.db.models import BooleanField
from django.db.models.lookups import Transform


class ST_IsEmpty(Transform):
    lookup_name = 'isempty'
    function = 'ST_ISEMPTY'
    output_field = BooleanField()
