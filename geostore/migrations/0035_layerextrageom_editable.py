# Generated by Django 2.2.8 on 2019-12-10 10:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('geostore', '0034_auto_20191209_0902'),
    ]

    operations = [
        migrations.AddField(
            model_name='layerextrageom',
            name='editable',
            field=models.BooleanField(default=True),
        ),
    ]
