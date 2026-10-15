from django.contrib.admin import ModelAdmin
from django.contrib.auth.admin import UserAdmin
from django.utils.translation import gettext_lazy as _

from config.admin_site import custom_admin_site
from .models import CustomUser


class CustomUserAdmin(UserAdmin):
    list_display = (
        'username', 'email', 'first_name', 'last_name', 'email', 'avatar',
        'is_page_permitted', 'can_request_dashboard',
        'dashboard_request_status', 'is_staff', 'is_superuser',
        "can_view_pom" , "can_create_pom" , "can_update_pom", "can_delete_pom",
        
    )
    list_filter = (
        'is_page_permitted', 'can_request_dashboard',
        'dashboard_request_status', 'is_staff', 'is_superuser', 'is_active',
    )
    readonly_fields = (
        'last_login',
        'date_joined',
        'dashboard_request_used_at',
    )
    fieldsets = UserAdmin.fieldsets + (
        (_('Dashboard Access'), {
            'fields': (
                'is_page_permitted',
                'can_request_dashboard',
                'dashboard_request_used',
                'dashboard_request_used_at',
                'dashboard_request_status',
            )
        }),
        (_("Permissin Api"), {
            "fields": (
                "can_view_pom",
                "can_create_pom",
                "can_update_pom",
                "can_delete_pom",
                "can_view_api",
            )
        }),
        (_("Profile"), {
            "fields": (
                "avatar",
            )
        })

    )


# Register with the custom admin site
custom_admin_site.register(CustomUser, CustomUserAdmin)
