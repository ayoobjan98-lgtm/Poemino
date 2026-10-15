from django.conf import settings
from django.conf.urls.static import static
from django.urls import path, include, re_path

from config.admin_site import custom_admin_site



urlpatterns = [
    path('admin/', custom_admin_site.urls),
    path('rosetta/', include('rosetta.urls')),
    path('accounts/', include('accounts.urls')),
    # THIS LINE IS REQUIRED for authentication:video_verify to work
    path('authentication/', include('authentication.urls')),
    # Old verification app can stay or be removed (empty)  # optional, but harmless
    path('dashboard/', include('dashboard.urls')),

        # Swagger UI


    path('', include('MakerPom.urls')),
    path('api/', include('api.urls')),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    import debug_toolbar
    urlpatterns += [path('__debug__/', include(debug_toolbar.urls))]



handler400 = "config.error_views.error_400"
handler403 = "config.error_views.error_403"
handler404 = "config.error_views.error_404"
handler500 = "config.error_views.error_500"
