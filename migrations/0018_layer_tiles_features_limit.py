# Generated by Django 2.0.9 on 2018-11-09 17:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('terra', '0017_auto_20181109_0848'),
    ]

    operations = [
        migrations.AddField(
            model_name='layer',
            name='tiles_features_limit',
            field=models.PositiveIntegerField(default=10000, null=True),
        ),
    ]