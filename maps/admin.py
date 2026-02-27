from django.contrib import admin
from django.contrib.gis.admin import GISModelAdmin
from .models import Location, Category, Region


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
    list_display = ('name', 'category', 'region', 'is_published', 'created_at')
    list_filter = ('is_published', 'category', 'region')
    search_fields = ('name', 'description')
    list_editable = ('is_published',)
    readonly_fields = ('created_at', 'updated_at')