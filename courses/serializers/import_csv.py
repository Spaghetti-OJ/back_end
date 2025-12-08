from rest_framework import serializers


class CourseImportCSVSerializer(serializers.Serializer):
    """
    驗證課程匯入 CSV 的檔案。
    """

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

    file = serializers.FileField(
        required=True,
        allow_empty_file=False,
        help_text="含有學生資料的 CSV 檔案",
    )

    def validate_file(self, value):
        filename = (getattr(value, "name", None) or "").lower()
        if not filename.endswith(".csv"):
            raise serializers.ValidationError("File must be a CSV.")

        size = getattr(value, "size", None)
        if size is None or size <= 0:
            raise serializers.ValidationError("File is empty.")
        if size > self.MAX_FILE_SIZE:
            raise serializers.ValidationError("File size exceeds 5MB.")
        return value
