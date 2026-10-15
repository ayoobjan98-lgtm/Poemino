from rest_framework.routers import DefaultRouter
from .viewsets import CreatePoemViewSet, CustomUserViewSet, ProfileUserViewSet

router = DefaultRouter()
router.register("Poems", CreatePoemViewSet, basename="create-poem")
router.register("Accounts", CustomUserViewSet, basename="account-customuser")
router.register("Accounts", ProfileUserViewSet, basename="account-profile")



