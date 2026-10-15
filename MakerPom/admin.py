from django.contrib import admin
from .models import CreatPom

@admin.register(CreatPom)
class CreatePomAdmin(admin.ModelAdmin):
    list_display = ['id', "name", "created_at", "edited_at", "status"]
    list_display_links = ["id", "name"] 
    list_editable = ['status']
    # exclude = ('slug',) 
    # readonly_fields = ('slug',) 