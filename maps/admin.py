import json

from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from django.contrib.gis.geos import Point
from django.utils.html import mark_safe
from django.urls import path, reverse
from django.shortcuts import redirect, get_object_or_404, render
from django.contrib import messages

from .models import Location, Category, Region, Route, RouteLocation, Guide, HystoryOb, POICategory, Country, CountryPolygon


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
    list_display = ('name', 'country', 'category', 'region', 'is_published', 'created_at')
    list_filter = ('is_published', 'country', 'category', 'region')
    search_fields = ('name', 'description')
    list_editable = ('is_published',)
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Основна інформація', {
            'fields': ('name', 'description', 'category', 'region', 'country', 'author'),
        }),
        ('Медіа', {
            'fields': ('image', 'gx_media_links'),
        }),
        ('Геодані', {
            'fields': ('geom',),
        }),
        ('Публікація', {
            'fields': ('is_published', 'created_at', 'updated_at'),
        }),
    )

    gis_widget_kwargs = {
        'attrs': {
            'default_lat': 50.2549,
            'default_lon': 28.6586,
            'default_zoom': 9,
        }
    }

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-geojson/',
                self.admin_site.admin_view(self.import_geojson_view),
                name='location-import-geojson',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_geojson_url'] = reverse('admin:location-import-geojson')
        return super().changelist_view(request, extra_context=extra_context)

    def import_geojson_view(self, request):
        from django.contrib.gis.geos import GEOSGeometry

        results = None

        if request.method == 'POST':
            geojson_file       = request.FILES.get('geojson_file')
            default_category_id = request.POST.get('default_category') or None
            default_region_id   = request.POST.get('default_region') or None
            default_country_id  = request.POST.get('default_country') or None
            filter_polygon_id   = request.POST.get('filter_polygon') or None
            name_field          = request.POST.get('name_field', '').strip()
            is_published        = 'is_published' in request.POST

            default_category = Category.objects.filter(pk=default_category_id).first() if default_category_id else None
            default_region   = Region.objects.filter(pk=default_region_id).first()      if default_region_id   else None
            default_country  = Country.objects.filter(pk=default_country_id).first()    if default_country_id  else None
            filter_polygon   = CountryPolygon.objects.filter(pk=filter_polygon_id).first() if filter_polygon_id else None

            results = {'imported': 0, 'skipped': 0, 'errors': [], 'filtered_out': 0}

            try:
                raw  = geojson_file.read().decode('utf-8')
                data = json.loads(raw)
            except Exception as e:
                results['errors'].append(f'Помилка читання файлу: {e}')
                data = {}

            features  = data.get('features', [])
            cat_cache = {c.slug: c for c in Category.objects.all()}

            for i, feature in enumerate(features):
                try:
                    geom_data = feature.get('geometry', {})
                    if geom_data.get('type') != 'Point':
                        results['skipped'] += 1
                        continue

                    coords = geom_data.get('coordinates', [])
                    if len(coords) < 2:
                        results['skipped'] += 1
                        continue

                    lng, lat = float(coords[0]), float(coords[1])
                    pt = Point(lng, lat, srid=4326)

                    # Фільтр по полігону країни
                    if filter_polygon and not filter_polygon.geom.contains(pt):
                        results['filtered_out'] += 1
                        continue

                    props = feature.get('properties') or {}

                    # Ім'я: спочатку вибраний атрибут, потім стандартні
                    if name_field:
                        name = str(props.get(name_field) or '').strip()
                    else:
                        name = (props.get('name') or props.get('Name') or
                                props.get('nazva') or props.get('NAME') or '').strip()

                    if not name:
                        results['skipped'] += 1
                        continue

                    description = props.get('description') or props.get('desc') or ''
                    cat_slug    = props.get('category') or props.get('category_slug') or ''
                    category    = cat_cache.get(cat_slug) or default_category

                    Location.objects.create(
                        name=name[:200],
                        description=str(description)[:2000] if description else '',
                        geom=pt,
                        category=category,
                        region=default_region,
                        country=default_country,
                        is_published=is_published,
                    )
                    results['imported'] += 1
                except Exception as e:
                    results['errors'].append(f'Об\'єкт #{i + 1}: {e}')

            if results['imported']:
                self.message_user(
                    request,
                    f'✅ Імпортовано {results["imported"]} локацій.',
                    level=messages.SUCCESS,
                )

        # Полігони для JS-фільтрації у формі
        polygons_by_country = {}
        for poly in CountryPolygon.objects.select_related('country').only('id', 'name', 'country_id'):
            polygons_by_country.setdefault(poly.country_id, []).append({'id': poly.id, 'name': poly.name})

        return render(request, 'admin/maps/location/import_geojson.html', {
            'results': results,
            'categories': Category.objects.all(),
            'regions': Region.objects.all(),
            'countries': Country.objects.all(),
            'polygons_by_country_json': json.dumps(polygons_by_country),
            'title': 'Імпорт GeoJSON',
            'opts': Location._meta,
        })


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
    #  Custom URLs
    # ------------------------------------------------------------------ #
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                '<int:route_id>/build-osrm/',
                self.admin_site.admin_view(self.build_osrm_view),
                name='route-build-osrm',
            ),
            path(
                'import-gpx/',
                self.admin_site.admin_view(self.import_gpx_view),
                name='route-import-gpx',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_gpx_url'] = reverse('admin:route-import-gpx')
        return super().changelist_view(request, extra_context=extra_context)

    # ------------------------------------------------------------------ #
    #  GPX імпорт
    # ------------------------------------------------------------------ #
    def import_gpx_view(self, request):
        import xml.etree.ElementTree as ET
        from django.contrib.gis.geos import LineString as GEOSLineString, Point as GEOSPoint

        if request.method == 'POST':
            gpx_file = request.FILES.get('gpx_file')
            route_name = request.POST.get('route_name', '').strip()
            difficulty = request.POST.get('difficulty', 'easy')
            region_id = request.POST.get('region') or None
            is_published = 'is_published' in request.POST
            create_locs = 'create_locations' in request.POST
            category_id = request.POST.get('waypoint_category') or None

            region = Region.objects.filter(pk=region_id).first() if region_id else None
            category = Category.objects.filter(pk=category_id).first() if category_id else None

            try:
                content = gpx_file.read()
                root = ET.fromstring(content)

                # Визначаємо namespace (GPX 1.0 або 1.1)
                ns = ''
                if root.tag.startswith('{'):
                    ns = root.tag.split('}')[0] + '}'

                def t(name):
                    return f'{ns}{name}'

                # Збираємо точки треку
                track_pts = []
                track_name = ''

                for trk in root.findall(t('trk')):
                    el = trk.find(t('name'))
                    if el is not None and el.text:
                        track_name = el.text.strip()
                    for seg in trk.findall(t('trkseg')):
                        for pt in seg.findall(t('trkpt')):
                            track_pts.append((float(pt.get('lon')), float(pt.get('lat'))))

                # Якщо немає треку — шукаємо <rte>
                if not track_pts:
                    for rte in root.findall(t('rte')):
                        el = rte.find(t('name'))
                        if el is not None and el.text:
                            track_name = el.text.strip()
                        for pt in rte.findall(t('rtept')):
                            track_pts.append((float(pt.get('lon')), float(pt.get('lat'))))

                if len(track_pts) < 2:
                    raise ValueError('GPX не містить трек з мінімум 2 точками')

                final_name = route_name or track_name or gpx_file.name.rsplit('.', 1)[0]
                line = GEOSLineString(track_pts, srid=4326)

                route = Route.objects.create(
                    name=final_name[:200],
                    path=line,
                    difficulty=difficulty,
                    region=region,
                    is_published=is_published,
                    author=request.user,
                )

                # Вейпоїнти → Локації
                wpts_created = 0
                if create_locs:
                    for i, wpt in enumerate(root.findall(t('wpt'))):
                        lon = float(wpt.get('lon'))
                        lat = float(wpt.get('lat'))
                        name_el = wpt.find(t('name'))
                        wpt_name = (name_el.text.strip() if name_el is not None and name_el.text
                                    else f'Точка {i + 1}')
                        desc_el = wpt.find(t('desc'))
                        desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ''

                        loc = Location.objects.create(
                            name=wpt_name[:200],
                            description=desc,
                            geom=GEOSPoint(lon, lat, srid=4326),
                            category=category,
                            region=region,
                            is_published=is_published,
                        )
                        RouteLocation.objects.create(route=route, location=loc, order=i)
                        wpts_created += 1

                route.refresh_from_db()
                self.message_user(
                    request,
                    f'✅ Маршрут "{route.name}" імпортовано! '
                    f'{len(track_pts)} точок треку · {route.distance_km} км · '
                    f'{wpts_created} вейпоїнтів створено.',
                    level=messages.SUCCESS,
                )
                return redirect(reverse('admin:maps_route_change', args=[route.pk]))

            except Exception as exc:
                self.message_user(request, f'❌ Помилка: {exc}', level=messages.ERROR)

        return render(request, 'admin/maps/route/import_gpx.html', {
            'regions': Region.objects.all(),
            'categories': Category.objects.all(),
            'difficulty_choices': Route.DIFFICULTY_CHOICES,
            'title': 'Імпорт GPX маршруту',
            'opts': Route._meta,
        })

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
    actions = ['copy_to_locations']

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

    @admin.action(description='📋 Копіювати в Локації (геометрія, назва, опис, фото)')
    def copy_to_locations(self, request, queryset):
        from django.contrib.gis.geos import Point

        created_count = 0
        skipped_count = 0

        for obj in queryset:
            if not obj.name or not obj.geom:
                skipped_count += 1
                continue

            point_2d = Point(obj.geom.x, obj.geom.y, srid=4326)

            _, was_created = Location.objects.get_or_create(
                name=obj.name[:200],
                defaults={
                    'description': obj.description or '',
                    'geom': point_2d,
                    'is_published': obj.is_published,
                    'gx_media_links': obj.gx_media_links or '',
                },
            )
            if was_created:
                created_count += 1
            else:
                skipped_count += 1

        self.message_user(
            request,
            f'✅ Скопійовано {created_count} локацій. '
            f'Пропущено {skipped_count} (вже існують або без даних).',
            level=messages.SUCCESS if created_count else messages.WARNING,
        )


@admin.register(POICategory)
class POICategoryAdmin(admin.ModelAdmin):
    list_display = ('emoji', 'name', 'is_published')
    list_editable = ('is_published',)
    search_fields = ('name',)
    fields = ('name', 'emoji', 'query', 'is_published')


class CountryPolygonInline(admin.TabularInline):
    model = CountryPolygon
    extra = 0
    fields = ('name', 'geom_preview')
    readonly_fields = ('geom_preview',)
    verbose_name = 'Полігон'
    verbose_name_plural = '🗺️ Полігони'

    def geom_preview(self, obj):
        if obj.pk and obj.geom:
            return mark_safe(
                f'<span style="color:#27ae60;font-size:0.85em;">✅ Завантажено '
                f'({obj.geom.num_geom} частин)</span>'
            )
        return '—'
    geom_preview.short_description = 'Геометрія'


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ('name', 'extent_code', 'polygon_count', 'is_published')
    list_editable = ('is_published',)
    search_fields = ('name',)
    inlines = [CountryPolygonInline]

    def polygon_count(self, obj):
        return obj.polygons.count()
    polygon_count.short_description = 'Полігонів'

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'import-polygons/',
                self.admin_site.admin_view(self.import_polygons_general_view),
                name='country-import-polygons-general',
            ),
            path(
                '<int:country_id>/import-polygons/',
                self.admin_site.admin_view(self.import_polygons_view),
                name='country-import-polygons',
            ),
        ]
        return custom_urls + urls

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_polygons_url'] = reverse('admin:country-import-polygons-general')
        return super().changelist_view(request, extra_context)

    def change_view(self, request, object_id, form_url='', extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_polygons_url'] = reverse(
            'admin:country-import-polygons', args=[object_id]
        )
        return super().change_view(request, object_id, form_url, extra_context)

    def import_polygons_general_view(self, request):
        """Загальний імпорт полігонів з вибором країни."""
        from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon

        results = None
        selected_country = None

        if request.method == 'POST':
            country_id = request.POST.get('country')
            selected_country = Country.objects.filter(pk=country_id).first() if country_id else None

            if not selected_country:
                self.message_user(request, '❌ Оберіть країну.', level=messages.ERROR)
            else:
                files = request.FILES.getlist('geojson_files')
                replace_existing = 'replace_existing' in request.POST
                results = {'imported': 0, 'skipped': 0, 'files': 0, 'errors': []}

                if replace_existing:
                    selected_country.polygons.all().delete()

                for f in files:
                    results['files'] += 1
                    try:
                        raw = f.read().decode('utf-8')
                        data = json.loads(raw)
                    except Exception as e:
                        results['errors'].append(f'{f.name}: помилка читання — {e}')
                        continue

                    features = data.get('features') if data.get('type') == 'FeatureCollection' else [data]

                    for i, feature in enumerate(features):
                        try:
                            geom_data = feature.get('geometry') if feature.get('type') == 'Feature' else feature
                            if not geom_data:
                                results['skipped'] += 1
                                continue

                            geos = GEOSGeometry(json.dumps(geom_data), srid=4326)
                            if isinstance(geos, Polygon):
                                geos = MultiPolygon(geos)
                            elif not isinstance(geos, MultiPolygon):
                                results['skipped'] += 1
                                continue

                            props = feature.get('properties') or {} if feature.get('type') == 'Feature' else {}
                            name = (
                                props.get('name') or props.get('Name') or
                                props.get('nazva') or props.get('NAME') or
                                f'{f.name.rsplit(".", 1)[0]}_{i + 1}'
                            )

                            CountryPolygon.objects.create(
                                country=selected_country,
                                name=str(name)[:200],
                                geom=geos,
                            )
                            results['imported'] += 1
                        except Exception as e:
                            results['errors'].append(f'{f.name} #{i + 1}: {e}')

                if results['imported']:
                    self.message_user(
                        request,
                        f'✅ Імпортовано {results["imported"]} полігонів з {results["files"]} файлів '
                        f'для країни "{selected_country.name}".',
                        level=messages.SUCCESS,
                    )

        return render(request, 'admin/maps/country/import_polygons_general.html', {
            'countries': Country.objects.all(),
            'selected_country': selected_country,
            'results': results,
            'title': 'Імпорт полігонів країн',
            'opts': Country._meta,
        })

    def import_polygons_view(self, request, country_id):
        from django.contrib.gis.geos import GEOSGeometry, MultiPolygon, Polygon

        country = get_object_or_404(Country, pk=country_id)
        results = None

        if request.method == 'POST':
            files = request.FILES.getlist('geojson_files')
            replace_existing = 'replace_existing' in request.POST
            results = {'imported': 0, 'skipped': 0, 'files': 0, 'errors': []}

            if replace_existing:
                country.polygons.all().delete()

            for f in files:
                results['files'] += 1
                try:
                    raw = f.read().decode('utf-8')
                    data = json.loads(raw)
                except Exception as e:
                    results['errors'].append(f'{f.name}: помилка читання — {e}')
                    continue

                features = data.get('features') if data.get('type') == 'FeatureCollection' else [data]

                for i, feature in enumerate(features):
                    try:
                        geom_data = feature.get('geometry') if feature.get('type') == 'Feature' else feature
                        if not geom_data:
                            results['skipped'] += 1
                            continue

                        geos = GEOSGeometry(json.dumps(geom_data), srid=4326)

                        if isinstance(geos, Polygon):
                            geos = MultiPolygon(geos)
                        elif not isinstance(geos, MultiPolygon):
                            results['skipped'] += 1
                            continue

                        props = feature.get('properties') or {} if feature.get('type') == 'Feature' else {}
                        name = (
                            props.get('name') or props.get('Name') or
                            props.get('nazva') or props.get('NAME') or
                            f'{f.name.rsplit(".", 1)[0]}_{i + 1}'
                        )

                        CountryPolygon.objects.create(
                            country=country,
                            name=str(name)[:200],
                            geom=geos,
                        )
                        results['imported'] += 1
                    except Exception as e:
                        results['errors'].append(f'{f.name} #{i + 1}: {e}')

            if results['imported']:
                self.message_user(
                    request,
                    f'✅ Імпортовано {results["imported"]} полігонів з {results["files"]} файлів.',
                    level=messages.SUCCESS,
                )

        return render(request, 'admin/maps/country/import_polygons.html', {
            'country': country,
            'results': results,
            'title': f'Імпорт полігонів — {country.name}',
            'opts': Country._meta,
        })


@admin.register(CountryPolygon)
class CountryPolygonAdmin(GISModelAdmin):
    list_display = ('name', 'country')
    list_filter = ('country',)
    search_fields = ('name', 'country__name')

    gis_widget_kwargs = {
        'attrs': {
            'default_lat': 48.5,
            'default_lon': 24.5,
            'default_zoom': 6,
        }
    }

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context['import_polygons_url'] = reverse('admin:country-import-polygons-general')
        return super().changelist_view(request, extra_context)


@admin.register(Guide)
class GuideAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone')