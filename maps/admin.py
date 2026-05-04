from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.utils.html import mark_safe
from django.urls import path, reverse
from django.shortcuts import redirect, get_object_or_404
from django.contrib import messages

from .models import Location, Category, Region, Route, RouteLocation, Guide, HystoryOb, POICategory


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


class RouteLocationInline(admin.TabularInline):
    """Inline для впорядкованих точок маршруту."""
    model = RouteLocation
    extra = 1
    fields = ('order', 'location')
    ordering = ('order',)
    verbose_name = 'Точка маршруту'
    verbose_name_plural = '📍 Точки маршруту (задайте порядок)'


@admin.register(Route)
class RouteAdmin(GISModelAdmin):
    inlines = [RouteLocationInline]

    list_display = ('name', 'region', 'difficulty', 'distance_km', 'duration_min', 'is_published', 'created_at')
    list_filter = ('is_published', 'difficulty', 'region')
    search_fields = ('name', 'description')
    list_editable = ('is_published',)
    readonly_fields = ('distance_km', 'duration_min', 'created_at', 'updated_at', 'build_route_button')

    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'description', 'region', 'author')
        }),
        ('🗺️ Автоматичний маршрут (OSRM)', {
            'fields': ('build_route_button',),
            'description': (
                'Додайте точки маршруту нижче (розділ "Точки маршруту"), '
                'збережіть форму, потім натисніть кнопку щоб побудувати '
                'маршрут по реальних дорогах через OSRM.'
            ),
        }),

        ('Характеристики', {
            'fields': ('difficulty', 'distance_km', 'duration_min')
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

    # ------------------------------------------------------------------ #
    #  Кнопка "Побудувати по дорогах"
    # ------------------------------------------------------------------ #
    def build_route_button(self, obj):
        if not obj or not obj.pk:
            return mark_safe(
                '<span style="color:#999;">💾 Спочатку збережіть маршрут</span>'
            )

        count = obj.route_locations.count()

        if count < 2:
            return mark_safe(
                f'<span style="color:#e67e22;">⚠️ Додайте мінімум 2 точки маршруту нижче '
                f'(зараз: {count})</span>'
            )

        url = reverse('admin:route-build-osrm', args=[obj.pk])
        locations_preview = ', '.join(
            rl.location.name
            for rl in obj.route_locations.select_related('location').order_by('order')[:5]
        )
        if count > 5:
            locations_preview += f' ... (+{count - 5})'

        return mark_safe(
            f'<div style="margin: 4px 0;">'
            f'<a href="{url}" class="button" '
            f'style="padding:8px 16px; background:#1a6fa8; color:white; '
            f'border-radius:6px; text-decoration:none; font-weight:500; display:inline-block;">'
            f'🗺️ Побудувати маршрут по дорогах ({count} точок)</a>'
            f'<div style="margin-top:8px; color:#666; font-size:0.85em;">'
            f'Порядок: {locations_preview}</div>'
            f'</div>'
        )

    build_route_button.short_description = '🚗 Побудувати по дорогах (OSRM)'

    # ------------------------------------------------------------------ #
    #  Custom URL + View для виклику OSRM
    # ------------------------------------------------------------------ #
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:route_id>/build-osrm/',
                self.admin_site.admin_view(self.build_osrm_view),
                name='route-build-osrm',
            ),
        ]
        return custom_urls + urls

    def build_osrm_view(self, request, route_id):
        import requests as http_requests
        from django.contrib.gis.geos import LineString

        route = get_object_or_404(Route, pk=route_id)
        ordered = list(
            route.route_locations.select_related('location').order_by('order', 'id')
        )

        if len(ordered) < 2:
            self.message_user(
                request,
                '⚠️ Потрібно мінімум 2 точки для побудови маршруту.',
                level=messages.WARNING,
            )
            return redirect(f'../../{route_id}/change/')

        # Формуємо рядок координат для OSRM: lon,lat;lon,lat;...
        coords_str = ';'.join(
            f"{rl.location.geom.x},{rl.location.geom.y}"
            for rl in ordered
        )

        osrm_url = (
            f"https://router.project-osrm.org/route/v1/driving/{coords_str}"
            f"?overview=full&geometries=geojson"
        )

        try:
            resp = http_requests.get(osrm_url, timeout=15)
            resp.raise_for_status()
            data = resp.json()

            if data.get('code') == 'Ok':
                geojson_coords = data['routes'][0]['geometry']['coordinates']
                line = LineString(geojson_coords, srid=4326)

                route.path = line
                route.save()   # save() автоматично перерахує distance_km і duration_min

                # Читаємо оновлені значення з БД
                route.refresh_from_db()
                self.message_user(
                    request,
                    f'✅ Маршрут побудовано! '
                    f'Відстань: {route.distance_km} км, '
                    f'Час в дорозі: {route.duration_min} хв.',
                    level=messages.SUCCESS,
                )
            else:
                self.message_user(
                    request,
                    f'❌ OSRM повернув помилку: {data.get("code")} — {data.get("message", "")}',
                    level=messages.ERROR,
                )

        except http_requests.Timeout:
            self.message_user(
                request,
                '❌ OSRM не відповів (timeout). Перевірте інтернет-з\'єднання.',
                level=messages.ERROR,
            )
        except Exception as exc:
            self.message_user(
                request,
                f'❌ Помилка: {exc}',
                level=messages.ERROR,
            )

        return redirect(f'../../{route_id}/change/')


@admin.register(HystoryOb)
class HystoryObAdmin(GISModelAdmin):
    list_display = ('name', 'description_short', 'is_published')
    list_filter = ('is_published',)
    search_fields = ('name', 'description')
    list_editable = ('is_published',)

    gis_widget_kwargs = {
        'attrs': {
            'default_lat': 48.9226,
            'default_lon': 24.7111,
            'default_zoom': 9,
        }
    }

    def description_short(self, obj):
        if obj.description:
            return obj.description[:60] + ('…' if len(obj.description) > 60 else '')
        return '—'
    description_short.short_description = 'Опис'


@admin.register(POICategory)
class POICategoryAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'name', 'is_published')
    list_editable = ('is_published',)
    search_fields = ('name',)
    fields = ('name', 'emoji', 'query', 'is_published')


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone')