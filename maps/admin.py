from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import Location, Category, Region, Route, Guide


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'icon')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(Location)
class LocationAdmin(GISModelAdmin):
    list_display = ('name', 'category', 'region', 'is_published', 'created_at')
    list_filter = ('is_published', 'category', 'region')
    search_fields = ('name', 'description')
    list_editable = ('is_published',)
    readonly_fields = ('created_at', 'updated_at')

    # Центр карти — Житомирська область
    gis_widget_kwargs = {
        'attrs': {
            'default_lat': 50.2549,
            'default_lon': 28.6586,
            'default_zoom': 9,
        }
    }


@admin.register(Route)
class RouteAdmin(GISModelAdmin):
    list_display  = ('name', 'region', 'difficulty', 'distance_km', 'duration_min', 'is_published', 'created_at')
    list_filter   = ('is_published', 'difficulty', 'region')
    search_fields = ('name', 'description')
    list_editable = ('is_published',)
    readonly_fields = ('distance_km', 'duration_min', 'created_at', 'updated_at')
    filter_horizontal = ('locations',)

    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'description', 'region', 'author')
        }),
        ('Маршрут на карті', {
            'fields': ('path',),
            'description': (
                'Натисніть на карті щоб додати точки маршруту. '
                'Клікайте по черзі — буде намальована лінія.'
            ),
        }),
        ('Характеристики', {
            'fields': ('difficulty', 'distance_km', 'duration_min')
        }),
        ('Пов\'язані локації', {
            'fields': ('locations',),
            'classes': ('collapse',),
        }),
        ('Публікація', {
            'fields': ('is_published', 'created_at', 'updated_at')
        }),
    )

    # Центр карти — Житомирська область
    gis_widget_kwargs = {
        'attrs': {
            'default_lat': 50.2549,
            'default_lon': 28.6586,
            'default_zoom': 9,
        }
    }


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone')