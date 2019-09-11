from django.contrib.postgres.fields.jsonb import JSONField
from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class JSONFieldFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = Q()
        for param_name, param_value in request.query_params.items():
            try:
                field = (queryset.model
                                 ._meta
                                 .get_field(param_name.split('__')[0]))
            except FieldDoesNotExist:
                pass
            else:
                if isinstance(field, JSONField):
                    sub_query = Q(**{param_name: param_value})
                    try:
                        sub_query |= Q(**{param_name: int(param_value)})
                    except ValueError:
                        pass
                    query &= sub_query
        return queryset.filter(query)
