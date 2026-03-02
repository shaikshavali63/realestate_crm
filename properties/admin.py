from django.contrib import admin
from .models import Property, PropertyImage, PropertySale


class PropertyImageInline(admin.TabularInline):
    model = PropertyImage
    extra = 0


@admin.register(Property)
class PropertyAdmin(admin.ModelAdmin):
    list_display = ("title", "property_type", "listing_type", "location", "price", "status")
    inlines = [PropertyImageInline]


@admin.register(PropertyImage)
class PropertyImageAdmin(admin.ModelAdmin):
    list_display = ("property", "image", "created_at")


@admin.register(PropertySale)
class PropertySaleAdmin(admin.ModelAdmin):
    list_display = ("property", "buyer_name", "buyer_lead", "sold_price", "sold_on")

