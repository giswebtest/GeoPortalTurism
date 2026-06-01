import uuid
from django.db import migrations, models


def populate_uids(apps, schema_editor):
    """Заповнює uid унікальними UUID4 для всіх існуючих рядків."""
    for model_name in ('CountryPolygon', 'Location', 'Route'):
        Model = apps.get_model('maps', model_name)
        for obj in Model.objects.all():
            obj.uid = uuid.uuid4()
            obj.save(update_fields=['uid'])


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0014_location_add_gx_media_links'),
    ]

    operations = [
        # Крок 1 — додаємо поле як nullable (без unique), щоб уникнути конфлікту
        migrations.AddField(
            model_name='countrypolygon',
            name='uid',
            field=models.UUIDField(null=True, editable=False, verbose_name='UUID (OGC)'),
        ),
        migrations.AddField(
            model_name='location',
            name='uid',
            field=models.UUIDField(null=True, editable=False, verbose_name='UUID (OGC)'),
        ),
        migrations.AddField(
            model_name='route',
            name='uid',
            field=models.UUIDField(null=True, editable=False, verbose_name='UUID (OGC)'),
        ),
        # Крок 2 — заповнюємо унікальними uuid4 для кожного наявного рядка
        migrations.RunPython(populate_uids, migrations.RunPython.noop),
        # Крок 3 — встановлюємо NOT NULL + UNIQUE
        migrations.AlterField(
            model_name='countrypolygon',
            name='uid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID (OGC)'),
        ),
        migrations.AlterField(
            model_name='location',
            name='uid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID (OGC)'),
        ),
        migrations.AlterField(
            model_name='route',
            name='uid',
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID (OGC)'),
        ),
    ]
