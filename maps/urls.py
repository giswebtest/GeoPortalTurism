from django.urls import path
from . import views
from . import ogc_views

app_name = 'maps'

urlpatterns = [
    # ── Публічна карта ────────────────────────────────────────
    path('', views.index, name='index'),

    # ── Кастомні GeoJSON API ──────────────────────────────────
    path('api/hystory-ob/', views.hystory_ob_geojson, name='hystory_ob_geojson'),
    path('api/ivfrankdist/', views.ivfrankdist_geojson, name='ivfrankdist_geojson'),
    path('api/overpass/', views.overpass_proxy, name='overpass_proxy'),
    path('api/countries/<int:country_id>/polygons/', views.country_polygons_geojson, name='country_polygons_geojson'),
    path('api/routes/<int:route_id>/elevation/', views.route_elevation, name='route_elevation'),

    # ── OGC API Features Part 1 ───────────────────────────────
    path('ogc',                                           ogc_views.ogc_landing,     name='ogc_landing_noslash'),
    path('ogc/',                                          ogc_views.ogc_landing,     name='ogc_landing'),
    path('ogc/conformance/',                              ogc_views.ogc_conformance, name='ogc_conformance'),
    path('ogc/collections/',                              ogc_views.ogc_collections, name='ogc_collections'),
    path('ogc/collections/<str:collection_id>/',           ogc_views.ogc_collection,  name='ogc_collection'),
    path('ogc/collections/<str:collection_id>/metadata/', ogc_views.ogc_metadata,    name='ogc_metadata'),
    path('ogc/collections/locations/items/',              ogc_views.ogc_locations,   name='ogc_locations'),
    path('ogc/collections/routes/items/',                 ogc_views.ogc_routes,      name='ogc_routes'),
    path('ogc/collections/hystory-ob/items/',             ogc_views.ogc_hystory_ob,  name='ogc_hystory_ob'),
    path('ogc/collections/districts/items/',              ogc_views.ogc_districts,   name='ogc_districts'),
]