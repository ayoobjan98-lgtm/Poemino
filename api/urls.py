from django.urls import path, include

# from api.views import StaffTokenObtainPairView, LoginStaffUserAPIView, LoginUserAPIView, UserTokenObtainPairView, APITokenView
from api.swagger import CustomSwaggerView
from api.views import APITokenView
from .routers import router

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
)

urlpatterns = [
    path("", include(router.urls)),

    path(
        "auth/token/",
        APITokenView.as_view(),
        name="api-token-"
    ),
    path(
        "schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    # path(
    #     "docs/",
    #     SpectacularSwaggerView.as_view(
    #         url_name="schema"
    #     ),
    #     name="swagger-ui",
    # ),

    path(
        "docs/",
        CustomSwaggerView.as_view(
            url_name="schema"
        ),
        name="swagger-ui",
    ),

    # path(
    #     "token/",
    #     UserTokenObtainPairView.as_view(),
    #     name="token",
    # ),

    # path(
    #     "staff/token/",
    #     StaffTokenObtainPairView.as_view(),
    #     name="staff-token",
    # ),


    ]
