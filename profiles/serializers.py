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
    user_id = serializers.CharField(source="user.id") 

    # 來自 UserProfile
    student_id = serializers.CharField(allow_blank=True, allow_null=True)
    bio = serializers.CharField(allow_blank=True, required=False)
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
            "user_id",
            "student_id",
            "bio",
            "avatar",
        ]

    def get_role(self, obj):
        # 取 TextChoices 的 display：Student/Teacher/Admin
        return obj.user.get_identity_display()
    
class PublicProfileSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source="username", read_only=True)
    role = serializers.SerializerMethodField(read_only=True)
    email = serializers.EmailField(read_only=True)
    user_id = serializers.CharField(source="id", read_only=True)
    bio = serializers.CharField(source="userprofile.bio", read_only=True, allow_blank=True)
    avatar = serializers.ImageField(source="userprofile.avatar", read_only=True, allow_null=True)

    class Meta:
        model = User
        fields = ("username", "role", "email", "user_id", "bio", "avatar")

    def get_role(self, obj):
        return obj.get_identity_display()
    
class MeProfileUpdateSerializer(serializers.Serializer):
    real_name = serializers.CharField(required=False)
    email = serializers.EmailField(required=False)
    student_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True)
    avatar = serializers.ImageField(required=False, allow_null=True)

    def update(self, instance: UserProfile, validated_data):
        user = instance.user

        if "real_name" in validated_data:
            user.real_name = validated_data["real_name"]
        if "email" in validated_data:
            user.email = validated_data["email"]
        user.save()

        if "student_id" in validated_data:
            instance.student_id = validated_data["student_id"]
        if "bio" in validated_data:
            instance.bio = validated_data["bio"]
        if "avatar" in validated_data:
            # 允許上傳新頭像或傳 null 清空（前端就送 avatar=null）
            instance.avatar = validated_data["avatar"]

        instance.save()
        return instance

    def create(self, validated_data):
        raise NotImplementedError("Use update() with an existing UserProfile instance.")