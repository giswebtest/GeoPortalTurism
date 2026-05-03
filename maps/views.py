from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from .models import Location, Route, Guide


def index(request):
    locations = Location.objects.filter(is_published=True)
    routes = Route.objects.filter(is_published=True)
    guides = Guide.objects.all()

    return render(request, 'maps/index.html', {
        'locations': locations,
        'routes': routes,
        'guides': guides,
    })


def _table_geojson(table_name):
    """Повертає GeoJSON FeatureCollection з довільної PostGIS таблиці."""
    with connection.cursor() as cursor:
        cursor.execute(f"""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(ST_AsGeoJSON(t.*)::json), '[]'::json)
            )
            FROM {table_name} t
        """)
        return cursor.fetchone()[0]


def hystory_ob_geojson(request):
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT json_build_object(
                'type', 'FeatureCollection',
                'features', COALESCE(json_agg(ST_AsGeoJSON(t.*)::json), '[]'::json)
            )
            FROM hystory_ob t
            WHERE t.is_published = true
        """)
        data = cursor.fetchone()[0]
    return JsonResponse(data, safe=False)


def ivfrankdist_geojson(request):
    # PostGIS зберігає назви таблиць у нижньому регістрі якщо не в лапках
    try:
        data = _table_geojson('"IvFrankDist"')
    except Exception:
        data = _table_geojson('ivfrankdist')
    return JsonResponse(data, safe=False)