# profile/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from user.models import UserProfile 

User = get_user_model()

class MeProfileSerializer(serializers.ModelSerializer):
    # 來自 User
    real_name = serializers.CharField(source="user.real_name")
    user_name = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email")
    user_id = serializers.CharField(source="user.id") 

    # 來自 UserProfile
    student_id = serializers.CharField(allow_blank=True, allow_null=True)
    introduction = serializers.CharField(source="bio", allow_blank=True, required=False)

    # 顯示 choices 的「標籤」（Student/Teacher/Admin）
    role = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "real_name",
            "user_name",
            "role",
            "email",
            "user_id",
            "student_id",
            "introduction",
        ]

    def get_role(self, obj):
        # 取 TextChoices 的 display：Student/Teacher/Admin
        return obj.user.get_identity_display()
    
class PublicProfileSerializer(serializers.ModelSerializer):
    """查看他人公開資料（隱藏 real_name, student_id）"""
    user_name = serializers.CharField(source="username")

    class Meta:
        model = User
        fields = (
            "user_name",
            "role",
            "email",         
            "user_id",
            "introduction",
        )
