# Generated by Django 3.0.1 on 2020-01-07 12:40

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('geostore', '0033_featureextrageom_layerextrageom'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='layerextrageom',
            options={'ordering': ('layer', 'order')},
        ),
        migrations.RenameField(
            model_name='layerrelation',
            old_name='schema',
            new_name='settings',
        ),
        migrations.AddField(
            model_name='featurerelation',
            name='relation',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, related_name='related_features', to='geostore.LayerRelation'),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='layerextrageom',
            name='editable',
            field=models.BooleanField(default=True),
        ),
        migrations.AddField(
            model_name='layerextrageom',
            name='order',
            field=models.PositiveSmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='layerrelation',
            name='exclude',
            field=django.contrib.postgres.fields.jsonb.JSONField(blank=True, default=dict, help_text='qs exclude (ex: {"pk__in": [...], "identifier__in":[...]}'),
        ),
        migrations.AddField(
            model_name='layerrelation',
            name='name',
            field=models.CharField(default='', max_length=250),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='layerrelation',
            name='relation_type',
            field=models.CharField(blank=True, choices=[(None, 'Manuelle'), ('intersects', 'Intersects'), ('distance', 'Distance')], default=(None, 'Manuelle'), max_length=25),
        ),
        migrations.AddField(
            model_name='layerrelation',
            name='slug',
            field=models.SlugField(default='', editable=False),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='featurerelation',
            name='destination',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relations_as_destination', to='geostore.Feature'),
        ),
        migrations.AlterField(
            model_name='featurerelation',
            name='origin',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='relations_as_origin', to='geostore.Feature'),
        ),
        migrations.AlterUniqueTogether(
            name='layerrelation',
            unique_together={('name', 'origin')},
        ),
        migrations.AddConstraint(
            model_name='feature',
            constraint=models.CheckConstraint(check=models.Q(geom__isvalid=True), name='geom_is_valid'),
        ),
    ]
