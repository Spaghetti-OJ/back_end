from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from user.models import UserProfile 
from .serializers import MeProfileSerializer, PublicProfileSerializer
from rest_framework import permissions
from rest_framework.generics import RetrieveAPIView
from rest_framework.exceptions import NotFound

User = get_user_model()

class MeProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # 盡量一次取回關聯
        user = User.objects.select_related("userprofile").get(pk=request.user.pk)
        # 若還沒建 Profile，先建立一個空的（避免前端 404）
        profile, _ = UserProfile.objects.get_or_create(user=user)
        data = MeProfileSerializer(profile).data
        return Response(data, status=200)

class PublicProfileView(RetrieveAPIView):
    """
    GET /profile/{username}/
    - 必須登入（JWT）
    - 回傳對方公開資料（不含 real_name、student_id）
    """
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = PublicProfileSerializer
    lookup_field = "username"
    queryset = User.objects.all()

    def get_object(self):
        username = self.kwargs.get(self.lookup_field)
        try:
            # 若你的系統 username 不分大小寫，可改成 username__iexact
            return self.get_queryset().get(username=username)
        except User.DoesNotExist:
            raise NotFound(detail="User not found.")