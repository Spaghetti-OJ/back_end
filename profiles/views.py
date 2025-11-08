from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.contrib.auth import get_user_model
from ..user.models import UserProfile 
from .serializers import MeProfileSerializer

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
