from django.core.exceptions import ValidationError
from django.db import models
from django.utils.translation import gettext as _


class PgRoutingMixin(models.Model):
    source = models.IntegerField(null=True,
                                 blank=True,
                                 help_text='Internal field used by pgRouting',
                                 editable=False)
    target = models.IntegerField(null=True,
                                 blank=True,
                                 help_text='Internal field used by pgRouting',
                                 editable=False)

    class Meta:
        abstract = True


class UpdateRoutingMixin(models.Model):
    routable = models.BooleanField(default=False, help_text='Used for make layer routable')

    def clean(self, *args, **kwargs):
        if self.routable and not self.is_linestring:
            raise ValidationError(_('Invalid geom type for routing'), code='invalid')
        super().clean(*args, **kwargs)

    class Meta:
        abstract = True
