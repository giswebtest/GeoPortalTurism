from django.urls import path
from . import views

app_name = 'maps'

urlpatterns = [
    path('', views.index, name='index'),
    path('api/hystory-ob/', views.hystory_ob_geojson, name='hystory_ob_geojson'),
    path('api/ivfrankdist/', views.ivfrankdist_geojson, name='ivfrankdist_geojson'),
]