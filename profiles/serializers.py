# profile/serializers.py
from rest_framework import serializers
from django.contrib.auth import get_user_model
from user.models import UserProfile 

User = get_user_model()

class MeProfileSerializer(serializers.ModelSerializer):
    # 來自 User
    real_name = serializers.CharField(source="user.real_name")
    username = serializers.CharField(source="user.username")
    email = serializers.EmailField(source="user.email")
    userid = serializers.CharField(source="user.id") 

    # 來自 UserProfile
    student_id = serializers.CharField(allow_blank=True, allow_null=True)
    introduction = serializers.CharField(source="bio", allow_blank=True, required=False)
    avatar = serializers.ImageField(allow_null=True, required=False)

    # 顯示 choices 的「標籤」（Student/Teacher/Admin）
    role = serializers.SerializerMethodField()

    class Meta:
        model = UserProfile
        fields = [
            "real_name",
            "username",
            "role",
            "email",
            "userid",
            "student_id",
            "introduction",
            "avatar",
        ]

    def get_role(self, obj):
        # 取 TextChoices 的 display：Student/Teacher/Admin
        return obj.user.get_identity_display()
    
class PublicProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="username", read_only=True)
    role = serializers.SerializerMethodField(read_only=True)
    email = serializers.EmailField(read_only=True)
    userid = serializers.CharField(source="id", read_only=True)
    introduction = serializers.CharField(source="userprofile.bio", read_only=True, allow_blank=True)
    avatar = serializers.ImageField(source="userprofile.avatar", read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ("username", "role", "email", "userid", "introduction", "avatar")

    def get_role(self, obj):
        return obj.get_identity_display()