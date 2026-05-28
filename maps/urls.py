from django.urls import path
from . import views

app_name = 'maps'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/hystory-ob/', views.hystory_ob_geojson, name='hystory_ob_geojson'),
    path('api/ivfrankdist/', views.ivfrankdist_geojson, name='ivfrankdist_geojson'),
    path('api/overpass/', views.overpass_proxy, name='overpass_proxy'),
    path('api/countries/<int:country_id>/polygons/', views.country_polygons_geojson, name='country_polygons_geojson'),
    path('api/routes/<int:route_id>/elevation/', views.route_elevation, name='route_elevation'),
]