from django.db import models


class PgRoutingMixin(models.Model):
    source = models.IntegerField(null=True,
                                 blank=True,
                                 help_text='Internal field used by pgRouting')
    target = models.IntegerField(null=True,
                                 blank=True,
                                 help_text='Internal field used by pgRouting')

    class Meta:
        abstract = True
