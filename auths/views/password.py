# auths/views/change_password.py
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from ..serializers.password import ChangePasswordSerializer
from rest_framework.response import Response

def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response(
        {
            "data": data,
            "message": message,
            "status": status_str,
        },
        status=status_code,
    )

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request},
        )
        if not serializer.is_valid():
            return api_response(
                data=serializer.errors,
                message="Invalid password.",
                status_code=400,
            )

        serializer.save()
        return api_response(
            data=None,
            message="Password changed successfully.",
            status_code=200,
        )