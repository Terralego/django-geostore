from django.core.exceptions import ObjectDoesNotExist
from django.http import Http404


class MultipleFieldLookupMixin(object):
    """
    Apply this mixin to any view or viewset to get multiple field filtering
    based on a `lookup_fields` attribute, instead of the default single field
    filtering.
    """
    def get_object(self):

        queryset = self.get_queryset()             # Get the base queryset
        queryset = self.filter_queryset(queryset)  # Apply any filter backends

        value = self.kwargs[self.lookup_field]
        for field in self.lookup_fields:
            try:
                obj = queryset.get(**{field: value})
            except (ObjectDoesNotExist, ValueError):
                continue
            else:
                self.check_object_permissions(self.request, obj)
                return obj
        raise Http404
