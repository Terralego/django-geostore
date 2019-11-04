from django.contrib.auth.models import Group
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode
from token_tools.generator import TokenGenerator

from .models import Layer, LayerGroup


class GroupTilesToken(TokenGenerator):

    def get_groups_intersect(self, user, layergroup):
        return Group.objects.filter(
            Q(authorized_layers__in=Layer.objects.filter(layer_groups__in=[layergroup, ])) &
            Q(pk__in=user.groups.all())
        )

    def decode_idb64(self, idb64):
        decoded = super().decode_idb64(idb64)
        if decoded is not None and '-' in decoded:
            gids, lid = decoded.rsplit('-', 1)

            try:
                gids = [int(gid) for gid in gids.split('-') if gid]
                return Group.objects.filter(pk__in=gids), LayerGroup.objects.get(pk=lid)
            except (ObjectDoesNotExist, ValueError):
                pass
        return None, None

    def token_idb64(self, groups, layergroup):
        # idb64 must be group parsable content to get back all group ids
        return urlsafe_base64_encode(force_bytes('-'.join([str(g.pk) for g in groups.distinct()]) + f'-{layergroup.pk}'))

    def _make_hash_value(self, groups, layergroup):
        # We use last updated layer timestamp, so when a layer is updated token changes
        last_update = layergroup.layers.all().order_by('updated_at').first().updated_at.replace(microsecond=0, tzinfo=None)
        return '-'.join([str(g.pk) for g in groups.distinct()]) + str(last_update)


tiles_token_generator = GroupTilesToken()
