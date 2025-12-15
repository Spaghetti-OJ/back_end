from rest_framework import serializers
from django.contrib.auth import get_user_model
from user.models import UserProfile

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.ChoiceField(
        source="identity",
        choices=[c.value for c in User.Identity],
        required=True,
    )

    student_id = serializers.CharField(
        source="userprofile.student_id", required=False, allow_blank=True, allow_null=True
    )
    bio = serializers.CharField(
        source="userprofile.bio", required=False, allow_blank=True, allow_null=True
    )

    class Meta:
        model = User
        fields = ["id", "username", "email", "password", "real_name", "role", "student_id", "bio"]
        extra_kwargs = {"password": {"write_only": True}}

    def create(self, validated_data):
        profile_data = validated_data.pop("userprofile", {})
        password = validated_data.pop("password")

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        UserProfile.objects.update_or_create(user=user, defaults=profile_data)
        return user

class MeSerializer(serializers.Serializer):
    user_id = serializers.CharField(source="id", read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(source="identity", read_only=True)
    email_verified = serializers.BooleanField(
        source="userprofile.email_verified",
        read_only=True,
    )