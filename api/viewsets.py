from django.contrib.auth import get_user_model

from rest_framework import mixins
from rest_framework.viewsets import GenericViewSet, ModelViewSet
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.decorators import action
from rest_framework.filters import SearchFilter
from django_filters.rest_framework import DjangoFilterBackend


from MakerPom.models import CreatPom

from .serializers import CreatePoemSerializer, CustomUserSerializer, ProfileSerializer
from .permissions import DjangoModelPermissions


User = get_user_model()

class CreatePoemViewSet(ModelViewSet):

    queryset = (
        CreatPom.objects
        .select_related("author")
        .filter(status="a")
    )

    serializer_class = CreatePoemSerializer
    permission_classes = [DjangoModelPermissions]

    filter_backends = [
        DjangoFilterBackend,
        SearchFilter,
    ]

    filterset_fields = [
        "status",
        "poem_type",
    ]

    search_fields = [
        "name",
        "text",
    ]

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)
        
class CustomUserViewSet(GenericViewSet):
    queryset = User.objects.nano()
    serializer_class = CustomUserSerializer

    @action(
        detail=False,
        methods=["get", "patch"],
        url_path="me",
        permission_classes=[IsAuthenticated],
    )
    def me(self, request):
        if request.method == "GET":
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

class ProfileUserViewSet(GenericViewSet):
    queryset = User.objects.nano()
    serializer_class = ProfileSerializer

    @action(
        detail=False,
        methods=["get", "patch"],
        url_path="profile",
        permission_classes=[IsAuthenticated],
    )
    def profile(self, request):
        if request.method == "GET":
            serializer = self.get_serializer(request.user)
            return Response(serializer.data)

        
        serializer = self.get_serializer(
            request.user,
            data=request.data,
            partial=True,
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)
        