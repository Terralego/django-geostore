from rest_framework.permissions import BasePermission, SAFE_METHODS


class LayerPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method in SAFE_METHODS:
            return True
        else:
            return request.user.has_perm('geostore.can_manage_layers')

    def has_object_permission(self, request, view, obj):
        if request.user.is_superuser:
            return True

        has_perm = request.user.has_perm('geostore.can_manage_layers')

        if obj.authorized_groups.exists():
            # Checking permissions if the layer has group authorizations
            if request.method not in SAFE_METHODS and not has_perm:
                return False

            return request.user.groups.filter(
                pk__in=list(obj.authorized_groups.values_list('pk', flat=True))
            ).exists()

        else:
            # else we check normal privileges
            return (request.method in SAFE_METHODS) or has_perm


class LayerImportExportPermission(BasePermission):
    def has_permission(self, request, view):
        if request.method not in SAFE_METHODS:
            return request.user.has_perm('geostore.can_import_layers')

        else:
            return request.user.has_perm('geostore.can_export_layers')


class FeaturePermission(LayerPermission):
    def has_object_permission(self, request, view, obj):
        return super().has_object_permission(request, view, obj.layer)
