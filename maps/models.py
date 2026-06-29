import uuid
from django.contrib.gis.db import models
from django.contrib.auth.models import User


class Region(models.Model):
    """Регион/область"""
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True)

    class Meta:
        verbose_name = 'Регион'
        verbose_name_plural = 'Регионы'

    def __str__(self):
        return self.name


class Category(models.Model):
    """Категория места"""
    name = models.CharField(max_length=100, verbose_name='Название')
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, default='📍', verbose_name='Иконка')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        ordering = ['name']

    def __str__(self):
        return self.name


class Location(models.Model):
    """Туристическое место"""
    uid  = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID (OGC)')
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')

    # Геоданные
    geom = models.PointField(srid=4326, geography=True, verbose_name='Координаты')

    # Связи
    country = models.ForeignKey(
        'Country', on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Територія',
        related_name='locations',
    )
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Регион'
    )
    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Категория'
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Автор'
    )

    # Медиа
    image = models.ImageField(
        upload_to='locations/',
        blank=True, null=True,
        verbose_name='Фото'
    )
    gx_media_links = models.URLField(
        max_length=500,
        blank=True,
        verbose_name='Фото (URL)',
        help_text='Пряме посилання на фото (з Google My Maps / Wikipedia)',
    )

    # Статус
    is_published = models.BooleanField(default=False, verbose_name='Опубликовано')

    # Даты
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Локация'
        verbose_name_plural = 'Локации'

    def __str__(self):
        return self.name


class Route(models.Model):
    """Туристичний маршрут"""
    uid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID (OGC)')

    DIFFICULTY_CHOICES = [
        ('easy',   '🟢 Легкий'),
        ('medium', '🟡 Середній'),
        ('hard',   '🔴 Складний'),
    ]

    name        = models.CharField(max_length=200, verbose_name='Назва')
    description = models.TextField(blank=True, verbose_name='Опис')

    # Геометрія маршруту — лінія через точки
    path = models.LineStringField(
        srid=4326, geography=True,
        null=True, blank=True,
        verbose_name='Маршрут на карті'
    )

    # Зв'язки
    region = models.ForeignKey(
        Region, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Регіон'
    )
    locations = models.ManyToManyField(
        Location, blank=True,
        through='RouteLocation',
        verbose_name='Точки маршруту'
    )
    author = models.ForeignKey(
        User, on_delete=models.SET_NULL,
        null=True, blank=True,
        verbose_name='Автор'
    )

    # Характеристики
    difficulty   = models.CharField(
        max_length=10, choices=DIFFICULTY_CHOICES,
        default='easy', verbose_name='Складність'
    )
    distance_km  = models.DecimalField(
        max_digits=6, decimal_places=2,
        null=True, blank=True,
        verbose_name='Відстань (км)'
    )
    duration_min = models.PositiveIntegerField(
        null=True, blank=True,
        verbose_name='Тривалість (хв)'
    )

    # Статус
    is_published = models.BooleanField(default=False, verbose_name='Опубліковано')

    # Дати
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name        = 'Маршрут'
        verbose_name_plural = 'Маршрути'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Спочатку зберігаємо об'єкт (щоб він з'явився в базі)
        super().save(*args, **kwargs)

        if self.path:
            # Використовуємо PostGIS для точного розрахунку відстані по сфері
            from django.contrib.gis.db.models.functions import Length
            # Отримуємо цей самий маршрут з бази, але з анотованою довжиною
            # Length для geography автоматично повертає значення в метрах
            db_route = Route.objects.annotate(calc_length=Length('path')).get(pk=self.pk)
            
            # Якщо calc_length повернуло значення
            if db_route.calc_length:
                # Отримуємо метри (.m) і переводимо в кілометри
                length_in_meters = db_route.calc_length.m
                calculated_distance = round(length_in_meters / 1000, 2)

                # Розрахунок тривалості
                speed_multiplier = {
                    'easy': 12,    # 12 хв на 1 км
                    'medium': 15,  # 15 хв на 1 км
                    'hard': 20     # 20 хв на 1 км
                }
                minutes_per_km = speed_multiplier.get(self.difficulty, 12)
                calculated_duration = int(float(calculated_distance) * minutes_per_km)

                # Оновлюємо поля напряму в базі (щоб не викликати save() ще раз і уникнути зациклення)
                Route.objects.filter(pk=self.pk).update(
                    distance_km=calculated_distance,
                    duration_min=calculated_duration
                )



class RouteLocation(models.Model):
    """Впорядкована точка маршруту (через-модель для Route.locations)"""
    route = models.ForeignKey(
        Route, on_delete=models.CASCADE,
        related_name='route_locations',
        verbose_name='Маршрут'
    )
    location = models.ForeignKey(
        Location, on_delete=models.CASCADE,
        verbose_name='Локація'
    )
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Порядок'
    )

    class Meta:
        ordering = ['order', 'id']
        verbose_name = 'Точка маршруту'
        verbose_name_plural = 'Точки маршруту'
        unique_together = [('route', 'location')]

    def __str__(self):
        return f"{self.order}. {self.location.name}"


class POICategory(models.Model):
    name = models.CharField(max_length=100, verbose_name='Назва')
    emoji = models.CharField(max_length=10, default='📍', verbose_name='Emoji')
    query = models.TextField(verbose_name='Запит Overpass API')
    is_published = models.BooleanField(default=False, verbose_name='Опубліковано')

    class Meta:
        verbose_name = 'POI Категорія'
        verbose_name_plural = 'POI Категорії'
        ordering = ['name']

    def __str__(self):
        return f'{self.emoji} {self.name}'


class HystoryOb(models.Model):
    """Пам'ятки культури — існуюча PostGIS таблиця hystory_ob (managed=False)."""
    geom = models.PointField(srid=4326, dim=3, null=True, blank=True, verbose_name='Координати')
    name = models.CharField(max_length=500, db_column='Name', blank=True, null=True, verbose_name='Назва')
    description = models.CharField(max_length=2000, blank=True, null=True, verbose_name='Опис')
    is_published = models.BooleanField(default=False, verbose_name='Опубліковано')

    class Meta:
        managed = False
        db_table = 'hystory_ob'
        verbose_name = "Пам'ятка культури"
        verbose_name_plural = "Пам'ятки культури"

    def __str__(self):
        return self.name or f'Об\'єкт #{self.id}'


class Country(models.Model):
    """Територія (країна або область) — назва та екстент карти."""
    name = models.CharField(max_length=200, verbose_name='Назва')
    extent_code = models.CharField(
        max_length=200,
        verbose_name='Код екстенту',
        help_text='Формат: minLng,minLat,maxLng,maxLat  (напр. 22.15,47.73,26.16,48.75)',
        blank=True,
    )
    is_published = models.BooleanField(default=False, verbose_name='Опубліковано')

    class Meta:
        verbose_name = 'Територія'
        verbose_name_plural = 'Території'
        ordering = ['name']

    def __str__(self):
        return self.name


class CountryPolygon(models.Model):
    """Полігон, прив'язаний до території."""
    uid     = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name='UUID (OGC)')
    country = models.ForeignKey(
        Country, on_delete=models.CASCADE,
        related_name='polygons',
        verbose_name='Територія',
    )
    name = models.CharField(max_length=200, verbose_name='Назва полігону')
    geom = models.MultiPolygonField(srid=4326, verbose_name='Геометрія')

    class Meta:
        verbose_name = 'Полігон території'
        verbose_name_plural = 'Полігони територій'
        ordering = ['country', 'name']

    def __str__(self):
        return f'{self.country.name} — {self.name}'


class Guide(models.Model):
    name = models.CharField(max_length=100, verbose_name='Ім\'я')
    phone = models.CharField(max_length=20, verbose_name='Телефон')
    image = models.ImageField(
        upload_to='guides/',
        blank=True, null=True,
        verbose_name='Фото'
    )
    class Meta:
        verbose_name = 'Гід'
        verbose_name_plural = 'Гіди'

    def __str__(self):
        return self.name
