from django.http import JsonResponse
from django.views import View
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from MakerPom.models import CreatPom
from api.services.token_service import create_api_token

from .filters import filter_poems
from .serializers import APITokenSerializer, ProfileSerializer, CreatePoemSerializer

import json

class APITokenView(APIView):

    authentication_classes = [
        SessionAuthentication,
    ]

    permission_classes = [
        IsAuthenticated,
    ]

    def post(self, request):
        token, api_role = create_api_token(request.user)

        data = {
            "access": str(token),
            "api_role": api_role,
            "expires_at": token["exp"],
        }

        serializer = APITokenSerializer(data)
        

        return Response(serializer.data)

class APITokenDataView(View):
    def get(self, request):
        return JsonResponse({})
    
    def post(self, request):
        token, api_role = create_api_token(request.user)
    
        data = {
            "access": str(token),
            "api_role": api_role,
            "expires_at": token["exp"],
        }
    
        serializer = APITokenSerializer(data=data)
        serializer.is_valid(raise_exception=True)
    
        return JsonResponse(
            serializer.validated_data
        )  


class ProfileAPIView(View):
    def get(self, request):
        # if not request.user.is_authenticated:
        #     return JsonResponse({})
        serilizer = ProfileSerializer(request.user)
        return JsonResponse(serilizer.data)     

    def post(self, request):
        # if not request.user.is_authenticated:
        #     return JsonResponse({})
        # if not request.data:
        #     return JsonResponse({})
        
        seralizer = ProfileSerializer(request.user, data=request.data)

        seralizer.is_valid()
        seralizer.save()

        return JsonResponse(seralizer.data)


class CreatePoemsAPIView(View):

    def get(self, request):

        # ---------------------------------------------------------
        # Base Query
        # فقط شعرهای تأیید شده
        # ---------------------------------------------------------

        poems = (
            CreatPom.objects
            .select_related("author")
            .filter(
                status=CreatPom.APPROVED
            )
        )

        # ---------------------------------------------------------
        # Filters
        # ---------------------------------------------------------

        poems = filter_poems(
            poems,
            request.GET
        )

        # ---------------------------------------------------------
        # Serialize
        # ---------------------------------------------------------

        serializer = CreatePoemSerializer(
            poems,
            many=True
        )

        # ---------------------------------------------------------
        # Response
        # ---------------------------------------------------------

        return JsonResponse(
            serializer.data,
            safe=False
        )


class CreatePoemDetailAPIView(View):
    def get(self, request, pk):
        data = CreatPom.objects.select_related("author").get(pk=pk) 
        serilizer = CreatePoemSerializer(data)
        return JsonResponse(serilizer.data)   

