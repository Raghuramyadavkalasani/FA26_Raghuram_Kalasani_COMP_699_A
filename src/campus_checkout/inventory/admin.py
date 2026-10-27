from django.contrib import admin
from .models import Equipment


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = ("asset_tag", "name", "category", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("asset_tag", "name", "category")
    actions = None

    def has_delete_permission(self, request, obj=None):
        # Retire inventory instead of deleting records that will acquire history.
        return False


admin.site.site_header = "Campus Equipment Checkout"
admin.site.site_title = "Equipment administration"
admin.site.index_title = "Inventory management"
