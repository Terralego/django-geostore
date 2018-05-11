from django.db.models import Func
from django.db.models import Aggregate
from django.db.models.fields import BooleanField, BinaryField

class ST_AsMVT(Aggregate):
    function = 'ST_AsMVT'
    output_field = BinaryField()
    template = "%(function)s(subquery, %(expressions)s)"

class ST_AsMvtGeom(Func):
    function = 'ST_AsMvtGeom'
    output_field = BinaryField()

class ST_Transform(Func):
    function = 'ST_Transform'
    output_field = BinaryField()

class ST_Intersects(Func):
    function = 'ST_Intersects'
    output_field = BooleanField()


class ST_MakeEnvelope(Func):
    function = 'ST_MakeEnvelope'
    output_field = BinaryField()