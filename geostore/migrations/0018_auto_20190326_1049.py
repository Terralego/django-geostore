# Generated by Django 2.0.13 on 2019-03-26 10:49

import django.contrib.postgres.indexes
from django.db import migrations, models
from django.contrib.postgres.operations import BtreeGistExtension


class Migration(migrations.Migration):

    dependencies = [
        ('geostore', '0017_auto_20181114_0806'),
    ]

    operations = [
        BtreeGistExtension(),
        migrations.AddIndex(
            model_name='feature',
            index=models.Index(fields=['identifier'], name='geo_featu_identif_212b28_idx'),
        ),
        migrations.AddIndex(
            model_name='feature',
            index=django.contrib.postgres.indexes.GistIndex(fields=['layer', 'geom'], name='geo_featu_layer_i_3dcdde_gist'),
        ),
    ]
