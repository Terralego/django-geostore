from django.db import migrations, models


def create_groups(apps, schema_editor):
    LayerGroup = apps.get_model('geostore', 'LayerGroup')
    LayerGroup.objects.create(name='default', slug='default')
    Layer = apps.get_model('geostore', 'Layer')
    for layer in Layer.objects.all():
        group_name = layer.group or 'default'
        group, created = LayerGroup.objects.get_or_create(name=group_name, defaults={'slug': group_name})
        group.layers.add(layer)


class Migration(migrations.Migration):

    dependencies = [
        ('geostore', '0026_auto_20190613_1529'),
    ]

    operations = [
        migrations.CreateModel(
            name='LayerGroup',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True,
                                        serialize=False, verbose_name='ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('name', models.CharField(max_length=256, unique=True)),
                ('slug', models.SlugField(unique=True)),
                ('layers', models.ManyToManyField(to='geostore.Layer', related_name='layer_groups')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.RunPython(create_groups),
    ]
