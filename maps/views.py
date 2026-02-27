from django.shortcuts import render
from django.http import HttpResponse
from django.core.serializers import serialize
from .models import Location

def index(request):
    locations = Location.objects.filter(is_published=True).select_related('category', 'region')
    return render(request, 'maps/index.html', {'locations': locations})
def locations_geojson(request):
    locations = Location.objects.filter(is_published=True)
    geojson = serialize('geojson', locations,
        geometry_field='geom',
        fields=['name', 'description']
    )
    return HttpResponse(geojson, content_type='application/json')