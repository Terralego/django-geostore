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
            is_authorized = any(map(
                lambda group: group in obj.authorized_groups.all(),
                request.user.groups()
            ))

            if request.method not in SAFE_METHODS:
                return is_authorized and has_perm

            return is_authorized

        else:
            # else we check normal privileges
            if request.method in SAFE_METHODS:
                return True
            else:
                return has_perm
