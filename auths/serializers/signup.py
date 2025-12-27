from rest_framework import serializers
from django.contrib.auth import get_user_model
from user.models import UserProfile
from courses.models import Course_members

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.CharField(source="identity", read_only=True)

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
        user.identity = User.Identity.STUDENT
        user.set_password(password)
        user.save()

        UserProfile.objects.update_or_create(user=user, defaults=profile_data)
        return user

class MeSerializer(serializers.Serializer):
    user_id = serializers.CharField(source="id", read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(source="identity", read_only=True)
    email_verified = serializers.SerializerMethodField()
    access_course = serializers.SerializerMethodField()

    def get_email_verified(self, obj):
        userprofile = getattr(obj, "userprofile", None)
        if userprofile is not None and hasattr(userprofile, "email_verified"):
            return userprofile.email_verified
        return False
    
    def get_access_course(self, user):
        qs = (
            Course_members.objects
            .filter(
                user_id=user,
                role__in=[Course_members.Role.TA, Course_members.Role.TEACHER],
            )
            .values_list("course_id_id", flat=True)
            .distinct()
        )
        return list(qs)