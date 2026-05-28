from django.shortcuts import render
from django.http import JsonResponse
from django.db import connection
from .models import Location, Route, Guide, Category, POICategory, Country, CountryPolygon


def index(request):
    locations = Location.objects.filter(is_published=True).select_related('category', 'region', 'country')
    routes = Route.objects.filter(is_published=True)
    guides = Guide.objects.all()
    categories = Category.objects.filter(location__is_published=True).distinct()
    poi_categories = POICategory.objects.filter(is_published=True)
    countries = Country.objects.filter(is_published=True)

    return render(request, 'maps/index.html', {
        'locations': locations,
        'routes': routes,
        'guides': guides,
        'categories': categories,
        'poi_categories': poi_categories,
        'countries': countries,
    })


def country_polygons_geojson(request, country_id):
    from django.core.serializers import serialize
    import json
    polygons = CountryPolygon.objects.filter(country_id=country_id).only('name', 'geom')
    data = json.loads(serialize('geojson', polygons, geometry_field='geom', fields=['name']))
    return JsonResponse(data, safe=False)


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


def overpass_proxy(request):
    query = request.GET.get('data', '')
    if not query:
        return JsonResponse({'error': 'No query'}, status=400)
    import requests as http_requests
    try:
        resp = http_requests.post(
            'https://overpass-api.de/api/interpreter',
            data={'data': query},
            headers={
                'User-Agent': 'GeoPortalTurism/1.0 (educational project)',
                'Accept': 'application/json',
            },
            timeout=30
        )
        resp.raise_for_status()
        return JsonResponse(resp.json(), safe=False)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)


def ivfrankdist_geojson(request):
    # PostGIS зберігає назви таблиць у нижньому регістрі якщо не в лапках
    try:
        data = _table_geojson('"IvFrankDist"')
    except Exception:
        data = _table_geojson('ivfrankdist')
    return JsonResponse(data, safe=False)


def route_elevation(request, route_id):
    import math
    import requests as http_requests
    from django.shortcuts import get_object_or_404

    route = get_object_or_404(Route, pk=route_id, is_published=True)
    if not route.path:
        return JsonResponse({'error': 'Маршрут не має геометрії'}, status=404)

    coords = list(route.path.coords)  # [(lon, lat), ...]

    MAX_POINTS = 100
    if len(coords) > MAX_POINTS:
        indices = [int(i * (len(coords) - 1) / (MAX_POINTS - 1)) for i in range(MAX_POINTS)]
        coords = [coords[i] for i in indices]

    def haversine_km(c1, c2):
        R = 6371.0
        lat1, lon1 = math.radians(c1[1]), math.radians(c1[0])
        lat2, lon2 = math.radians(c2[1]), math.radians(c2[0])
        dlat, dlon = lat2 - lat1, lon2 - lon1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        return R * 2 * math.asin(math.sqrt(a))

    distances = [0.0]
    for i in range(1, len(coords)):
        distances.append(distances[-1] + haversine_km(coords[i-1], coords[i]))

    locs = '|'.join(f'{c[1]},{c[0]}' for c in coords)
    try:
        resp = http_requests.get(
            f'https://api.opentopodata.org/v1/srtm90m?locations={locs}',
            timeout=20
        )
        resp.raise_for_status()
        results = resp.json().get('results', [])
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=502)

    profile = [
        {
            'distance_km': round(distances[i], 3),
            'elevation_m': round(r['elevation'], 1),
            'lat': round(coords[i][1], 6),
            'lng': round(coords[i][0], 6),
        }
        for i, r in enumerate(results)
        if r.get('elevation') is not None
    ]

    return JsonResponse({'profile': profile, 'name': route.name})