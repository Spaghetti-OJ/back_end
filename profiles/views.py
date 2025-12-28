from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from user.models import UserProfile 
from .serializers import MeProfileSerializer, MeProfileUpdateSerializer, PublicProfileSerializer
from rest_framework import permissions
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import NotFound
from user.permissions import IsEmailVerified

def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response({
        "data": data,
        "message": message,
        "status": status_str,
    }, status=status_code)

User = get_user_model()

class MeProfileView(APIView):
    #permission_classes = [IsAuthenticated, IsEmailVerified]
    skip_email_verification = True

    def get(self, request):
        # 盡量一次取回關聯
        user = User.objects.select_related("userprofile").get(pk=request.user.pk)
        # 若還沒建 Profile，先建立一個空的（避免前端 404）
        profile, _ = UserProfile.objects.get_or_create(user=user)
        data = MeProfileSerializer(profile).data
        
        return api_response(data=data, status_code=200)
    
    def post(self, request):
        user = User.objects.select_related("userprofile").get(pk=request.user.pk)
        profile, _ = UserProfile.objects.get_or_create(user=user)

        serializer = MeProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            profile.refresh_from_db()
            data = MeProfileSerializer(profile).data
            return api_response(data=data, message="Profile updated")

        return api_response(
            data=serializer.errors,
            message="Validation error",
            status_code=400,
        )

class PublicProfileView(RetrieveAPIView):
    """
    GET /profile/{username}/
    - 必須登入（JWT）
    - 回傳對方公開資料（不含 real_name、student_id）
    """
    #permission_classes = [IsAuthenticated, IsEmailVerified]
    serializer_class = PublicProfileSerializer
    lookup_field = "username"

    def get_queryset(self):
        return User._default_manager.select_related("userprofile")

    def get_object(self):
        key = (self.kwargs.get(self.lookup_field) or "").strip()
        try:
            return self.get_queryset().get(username__iexact=key)
        except User.DoesNotExist:
            raise NotFound("User not found.")

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(data=serializer.data, status_code=200)