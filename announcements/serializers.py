from django.contrib.auth import get_user_model
from rest_framework import serializers

from courses.models import Announcements, Courses

User = get_user_model()


class AnnouncementUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "real_name", "identity")


class SystemAnnouncementSerializer(serializers.ModelSerializer):
    annId = serializers.SerializerMethodField()
    markdown = serializers.CharField(source="content")
    pinned = serializers.BooleanField(source="is_pinned")
    creator = serializers.SerializerMethodField()
    updater = serializers.SerializerMethodField()
    createTime = serializers.SerializerMethodField()
    updateTime = serializers.SerializerMethodField()

    class Meta:
        model = Announcements
        fields = (
            "annId",
            "title",
            "createTime",
            "updateTime",
            "creator",
            "updater",
            "markdown",
            "pinned",
        )

    def get_annId(self, obj: Announcements):
        return str(obj.id)

    @staticmethod
    def _timestamp(dt):
        if dt is None:
            return None
        return int(dt.timestamp())

    def get_createTime(self, obj: Announcements):
        return self._timestamp(obj.created_at)

    def get_updateTime(self, obj: Announcements):
        return self._timestamp(obj.updated_at)

    def _user_payload(self, user: User | None):
        if user is None:
            return None
        return AnnouncementUserSerializer(user).data

    def get_creator(self, obj: Announcements):
        return self._user_payload(obj.creator_id)

    def get_updater(self, obj: Announcements):
        # Announcements model沒有獨立的 updater 欄位，因此回傳 creator 作為 updater
        return self._user_payload(obj.creator_id)


class AnnouncementCreateSerializer(serializers.ModelSerializer):
    course_id = serializers.PrimaryKeyRelatedField(queryset=Courses.objects.all())

    class Meta:
        model = Announcements
        fields = ("title", "content", "course_id", "is_pinned")
        extra_kwargs = {"is_pinned": {"required": False}}


class AnnouncementUpdateSerializer(serializers.Serializer):
    annId = serializers.IntegerField()
    title = serializers.CharField(max_length=200)
    context = serializers.CharField(required=False, write_only=True)
    content = serializers.CharField(required=False, write_only=True)
    is_pinned = serializers.BooleanField(required=False)

    def validate(self, attrs):
        text = attrs.get("context") or attrs.get("content")
        if text is None:
            raise serializers.ValidationError(
                {"context": ["This field is required."]}
            )

        attrs["content"] = text
        attrs.pop("context", None)
        return attrs


class AnnouncementDeleteSerializer(serializers.Serializer):
    annId = serializers.IntegerField()
