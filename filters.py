from django.core.exceptions import FieldDoesNotExist
from django.db.models import Q
from rest_framework.filters import BaseFilterBackend


class JSONFieldFilterBackend(BaseFilterBackend):
    def filter_queryset(self, request, queryset, view):
        query = Q()
        for param_name, param_value in request.query_params.items():
            try:
                queryset.model._meta.get_field(param_name.split('__')[0])
            except FieldDoesNotExist:
                pass
            else:
                try:
                    query |= (Q(**{param_name: int(param_value)})
                              | Q(**{param_name: param_value}))
                except ValueError:
                    query |= Q(**{param_name: param_value})
        return queryset.filter(query)
