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

    def __str__(self):
        return self.name


class Location(models.Model):
    """Туристическое место"""
    name = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(blank=True, verbose_name='Описание')

    # Геоданные
    geom = models.PointField(srid=4326, geography=True, verbose_name='Координаты')

    # Связи
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

