# Generated by Django 3.0.7 on 2020-06-25 15:15

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geostore', '0040_merge_20200625_1508'),
    ]

    operations = [
        migrations.RemoveIndex(
            model_name='feature',
            name='geostore_fe_propert_46222e_gin',
        ),
        migrations.AddIndex(
            model_name='feature',
            index=models.Index(fields=['source', 'target', 'layer'], name='geostore_fe_source_155396_idx'),
        ),
    ]
