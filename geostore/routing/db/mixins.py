from django.db import models


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
