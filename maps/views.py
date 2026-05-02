from django.shortcuts import render
from .models import Location, Route, Guide

def index(request):
    locations = Location.objects.filter(is_published=True)
    routes = Route.objects.filter(is_published=True)
    guides = Guide.objects.all()
    
    return render(request, 'maps/index.html', {
        'locations': locations,
        'routes': routes,
        'guides': guides
    })