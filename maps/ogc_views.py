"""
OGC API Features Part 1 — Core
Endpoints:
  GET /ogc/                                    Landing page
  GET /ogc/conformance/                        Conformance classes
  GET /ogc/collections/                        All collections
  GET /ogc/collections/<id>/                   Collection metadata
  GET /ogc/collections/<id>/items/             GeoJSON FeatureCollection
                                               ?bbox=minx,miny,maxx,maxy
                                               ?limit=10  (default 10, max 10000)
                                               ?offset=0
  GET /ogc/collections/<id>/metadata/          ISO 19115:2003/19139 XML
"""
import json
from django.http import JsonResponse, HttpResponse
from django.contrib.gis.geos import Polygon
from django.db import connection, ProgrammingError
from .models import Location, Route


# ── helpers ──────────────────────────────────────────────────────────────────

def _resp(data, geo=False):
    ct = 'application/geo+json' if geo else 'application/json'
    r = JsonResponse(data)
    r['Content-Type'] = ct + '; charset=utf-8'
    r['Access-Control-Allow-Origin'] = '*'
    r['Content-Language'] = 'uk'
    return r


def _pagination(request):
    try:
        limit = min(max(int(request.GET.get('limit', 10)), 1), 10000)
    except (ValueError, TypeError):
        limit = 10
    try:
        offset = max(int(request.GET.get('offset', 0)), 0)
    except (ValueError, TypeError):
        offset = 0
    return limit, offset


def _bbox_poly(bbox_str):
    """'minx,miny,maxx,maxy' → GEOS Polygon SRID 4326."""
    vals = [float(v) for v in bbox_str.split(',')]
    p = Polygon.from_bbox(vals)
    p.srid = 4326
    return p


def _fc(features, number_matched, request):
    return {
        'type': 'FeatureCollection',
        'numberMatched': number_matched,
        'numberReturned': len(features),
        'links': [{'href': request.build_absolute_uri(), 'rel': 'self', 'type': 'application/geo+json'}],
        'features': features,
    }


_BBOX_UA = [[22.15, 47.73, 26.16, 48.75]]
_CRS84   = 'http://www.opengis.net/def/crs/OGC/1.3/CRS84'

_COLLECTIONS_META = {
    'locations': {
        'title':       'Туристичні локації',
        'description': "Туристичні об'єкти Івано-Франківської та суміжних областей",
    },
    'routes': {
        'title':       'Туристичні маршрути',
        'description': 'Затверджені туристичні маршрути з геометрією LineString',
    },
    'hystory-ob': {
        'title':       "Пам'ятки культури",
        'description': "Об'єкти культурної спадщини (таблиця hystory_ob)",
    },
    'districts': {
        'title':       'Райони Івано-Франківської області',
        'description': 'Адміністративні райони (IvFrankDist)',
    },
}


def _collection_obj(cid, request):
    base = request.build_absolute_uri(f'/ogc/collections/{cid}')
    meta = _COLLECTIONS_META[cid]
    return {
        'id': cid,
        **meta,
        'itemType': 'feature',
        'crs': [_CRS84],
        'extent': {'spatial': {'bbox': _BBOX_UA, 'crs': _CRS84}},
        'links': [
            {'href': base + '/',           'rel': 'self',        'type': 'application/json'},
            {'href': base + '/items/',     'rel': 'items',       'type': 'application/geo+json',      'title': meta['title']},
            {'href': base + '/metadata/',  'rel': 'describedBy', 'type': 'application/xml',           'title': 'ISO 19115 metadata'},
        ],
    }


# ── Landing page ──────────────────────────────────────────────────────────────

def ogc_landing(request):
    base = request.build_absolute_uri('/ogc')
    return _resp({
        'title':       'GeoPortal Turism — OGC API Features',
        'description': "Геопросторовий портал туристичних ресурсів Івано-Франківської області",
        'links': [
            {'href': f'{base}/',             'rel': 'self',                                                   'type': 'application/json', 'title': 'This document'},
            {'href': f'{base}/conformance/', 'rel': 'conformance',                                            'type': 'application/json', 'title': 'OGC API conformance classes'},
            {'href': f'{base}/conformance/', 'rel': 'http://www.opengis.net/def/rel/ogc/1.0/conformance',    'type': 'application/json', 'title': 'OGC API conformance classes'},
            {'href': f'{base}/collections/', 'rel': 'data',                                                   'type': 'application/json', 'title': 'Collections'},
            {'href': f'{base}/collections/', 'rel': 'http://www.opengis.net/def/rel/ogc/1.0/data',           'type': 'application/json', 'title': 'Collections'},
        ],
    })


# ── Conformance ───────────────────────────────────────────────────────────────

def ogc_conformance(request):
    return _resp({
        'conformsTo': [
            'http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/core',
            'http://www.opengis.net/spec/ogcapi-features-1/1.0/conf/geojson',
        ]
    })


# ── Collections list ─────────────────────────────────────────────────────────

def ogc_collections(request):
    return _resp({
        'collections': [_collection_obj(cid, request) for cid in _COLLECTIONS_META],
        'links': [{'href': request.build_absolute_uri('/ogc/collections/'), 'rel': 'self', 'type': 'application/json'}],
    })


# ── Single collection metadata ────────────────────────────────────────────────

def ogc_collection(request, collection_id):
    if collection_id not in _COLLECTIONS_META:
        return _resp({'code': 'NotFound', 'description': f'Collection "{collection_id}" not found'}, False)
    return _resp(_collection_obj(collection_id, request))


# ── locations/items ───────────────────────────────────────────────────────────

def ogc_locations(request):
    limit, offset = _pagination(request)
    qs = Location.objects.filter(is_published=True).select_related('category', 'region', 'country')

    bbox = request.GET.get('bbox')
    if bbox:
        qs = qs.filter(geom__intersects=_bbox_poly(bbox))

    number_matched = qs.count()
    features = []
    for loc in qs[offset: offset + limit]:
        if not loc.geom:
            continue
        features.append({
            'type': 'Feature',
            'id': str(loc.uid),
            'geometry': json.loads(loc.geom.geojson),
            'properties': {
                'uid':           str(loc.uid),
                'name':          loc.name,
                'description':   loc.description or None,
                'category':      loc.category.name if loc.category else None,
                'category_icon': loc.category.icon if loc.category else None,
                'region':        loc.region.name   if loc.region   else None,
                'country':       loc.country.name  if loc.country  else None,
                'updated_at':    loc.updated_at.isoformat(),
            },
        })
    return _resp(_fc(features, number_matched, request), geo=True)


# ── routes/items ──────────────────────────────────────────────────────────────

def ogc_routes(request):
    limit, offset = _pagination(request)
    qs = Route.objects.filter(is_published=True)

    bbox = request.GET.get('bbox')
    if bbox:
        qs = qs.filter(path__intersects=_bbox_poly(bbox))

    number_matched = qs.count()
    features = []
    for route in qs[offset: offset + limit]:
        if not route.path:
            continue
        features.append({
            'type': 'Feature',
            'id': str(route.uid),
            'geometry': json.loads(route.path.geojson),
            'properties': {
                'uid':          str(route.uid),
                'name':         route.name,
                'description':  route.description or None,
                'difficulty':   route.difficulty,
                'distance_km':  float(route.distance_km)  if route.distance_km  else None,
                'duration_min': route.duration_min,
                'updated_at':   route.updated_at.isoformat(),
            },
        })
    return _resp(_fc(features, number_matched, request), geo=True)


# ── hystory-ob/items ──────────────────────────────────────────────────────────

def ogc_hystory_ob(request):
    limit, offset = _pagination(request)

    bbox_sql, bbox_params = '', []
    bbox = request.GET.get('bbox')
    if bbox:
        vals = [float(v) for v in bbox.split(',')]
        bbox_sql = 'AND ST_Intersects(geom, ST_MakeEnvelope(%s,%s,%s,%s,4326))'
        bbox_params = vals

    with connection.cursor() as cur:
        cur.execute(
            f'SELECT COUNT(*) FROM hystory_ob WHERE geom IS NOT NULL {bbox_sql}',
            bbox_params,
        )
        number_matched = cur.fetchone()[0]

        cur.execute(
            f"""SELECT id, "Name", description,
                       ST_AsGeoJSON(ST_Force2D(geom)) AS geojson
                FROM hystory_ob
                WHERE geom IS NOT NULL {bbox_sql}
                ORDER BY id LIMIT %s OFFSET %s""",
            bbox_params + [limit, offset],
        )
        rows = cur.fetchall()

    features = [
        {
            'type': 'Feature',
            'id': str(row_id),
            'geometry': json.loads(geojson),
            'properties': {'name': name or '', 'description': desc or ''},
        }
        for row_id, name, desc, geojson in rows
    ]
    return _resp(_fc(features, number_matched, request), geo=True)


# ── districts/items ───────────────────────────────────────────────────────────

def ogc_districts(request):
    limit, offset = _pagination(request)

    bbox_sql, bbox_params = '', []
    bbox = request.GET.get('bbox')
    if bbox:
        vals = [float(v) for v in bbox.split(',')]
        bbox_sql = 'WHERE ST_Intersects(geom, ST_MakeEnvelope(%s,%s,%s,%s,4326))'
        bbox_params = vals

    def _query(table):
        with connection.cursor() as cur:
            cur.execute(f'SELECT COUNT(*) FROM {table} {bbox_sql}', bbox_params)
            n = cur.fetchone()[0]
            cur.execute(
                f'SELECT id, ST_AsGeoJSON(geom) FROM {table} {bbox_sql} ORDER BY id LIMIT %s OFFSET %s',
                bbox_params + [limit, offset],
            )
            return n, cur.fetchall()

    try:
        number_matched, rows = _query('"IvFrankDist"')
    except ProgrammingError:
        number_matched, rows = _query('ivfrankdist')

    features = [
        {
            'type': 'Feature',
            'id': str(row_id),
            'geometry': json.loads(geojson),
            'properties': {'id': row_id},
        }
        for row_id, geojson in rows
    ]
    return _resp(_fc(features, number_matched, request), geo=True)


# ── ISO 19115 metadata ────────────────────────────────────────────────────────

def ogc_metadata(request, collection_id):
    """
    GET /ogc/collections/<id>/metadata/
    Повертає ISO 19115:2003/19139 XML для вказаної колекції.
    rel=describedBy  (OGC API — Features, Part 1, Req. 13)
    """
    from .iso19115 import generate_xml, collection_ids

    if collection_id not in collection_ids():
        return HttpResponse(
            f'<error>Collection "{collection_id}" not found</error>',
            content_type='application/xml', status=404,
        )

    base_url = request.build_absolute_uri('/').rstrip('/')
    xml = generate_xml(collection_id, base_url)

    resp = HttpResponse(xml, content_type='application/xml; charset=utf-8')
    resp['Access-Control-Allow-Origin'] = '*'
    resp['Content-Disposition'] = f'inline; filename="metadata_{collection_id}.xml"'
    return resp
