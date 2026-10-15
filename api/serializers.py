# api/serializers.py

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from MakerPom.models import CreatPom
from accounts.models import CustomUser, Profile
# from api.tokens import StaffRefreshToken, UserRefreshToken


# =================== Serializers Accounts =================

User = get_user_model()

class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User

        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "email",
        ]

        read_only_fields = [
            "id",
            "username",
        ]

class ProfileSerializer(serializers.ModelSerializer):     
    class Meta:
        model = User
        fields = [
            "username",
            "first_name",
            "last_name",
            "email",
            "avatar",
        ]

# =================== Serializers MakerPom =================

class AuthorSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "avatar",
        ]


class CreatePoemSerializer(serializers.ModelSerializer):
    author = AuthorSerializer(read_only=True)

    class Meta:
        model = CreatPom

        fields = [
            "id",
            "name",
            "text",
            "voies",
            "author",
            "status",
            "poem_type",
        ]

        read_only_fields = [
            "id",
            "author",
            "status",
        ]


# =================== JWT ===================

class APITokenSerializer(serializers.Serializer):

    access = serializers.CharField()

    api_role = serializers.CharField()

    expires_at = serializers.IntegerField()


# END