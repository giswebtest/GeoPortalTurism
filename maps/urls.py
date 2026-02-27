from django.urls import path
from . import views

app_name = 'maps'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/locations/', views.locations_geojson, name='locations_geojson'),
]