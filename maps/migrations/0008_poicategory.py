from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maps', '0007_hystoryob_is_published'),
    ]

    operations = [
        migrations.CreateModel(
            name='POICategory',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, verbose_name='Назва')),
                ('emoji', models.CharField(default='📍', max_length=10, verbose_name='Emoji')),
                ('query', models.TextField(verbose_name='Запит Overpass API')),
                ('is_published', models.BooleanField(default=False, verbose_name='Опубліковано')),
            ],
            options={
                'verbose_name': 'POI Категорія',
                'verbose_name_plural': 'POI Категорії',
                'ordering': ['name'],
            },
        ),
    ]
