from rest_framework import serializers
from django.contrib.auth import get_user_model
from user.models import UserProfile

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    identity = serializers.ChoiceField(
        choices=[c.value for c in User.Identity],  # ['teacher','admin','student']
        required=True
    )
    student_id = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    bio = serializers.CharField(required=False, allow_blank=True)

    class Meta:
        model = User
        fields = ['id','username','email','password','real_name','identity','student_id','bio']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        student_id = validated_data.pop('student_id', None)
        bio = validated_data.pop('bio', '')
        password = validated_data.pop('password')

        user = User(**validated_data)
        user.set_password(password)
        user.save()

        profile, _ = UserProfile.objects.get_or_create(user=user)
        if student_id is not None:
            profile.student_id = student_id
        if bio:
            profile.bio = bio
        profile.save()
        return user


class MeSerializer(serializers.Serializer):
    userid = serializers.CharField(source="id", read_only=True)
    username = serializers.CharField(read_only=True)
    email = serializers.EmailField(read_only=True)
    role = serializers.CharField(read_only=True)