# Generated by Django 3.2 on 2021-04-29 08:18

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geostore', '0044_auto_20201106_1638'),
    ]

    operations = [
        migrations.AddConstraint(
            model_name='featureextrageom',
            constraint=models.CheckConstraint(check=models.Q(geom__isvalid=True), name='geom_extra_is_valid'),
        ),
        migrations.AddConstraint(
            model_name='featureextrageom',
            constraint=models.CheckConstraint(check=models.Q(geom__isempty=False), name='geom_extra_is_empty'),
        ),
    ]
