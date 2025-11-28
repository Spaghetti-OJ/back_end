from rest_framework.views import APIView
from rest_framework import status
from django.contrib.auth import get_user_model
from rest_framework.permissions import IsAuthenticated

from rest_framework.response import Response

def api_response(data=None, message="OK", status_code=200):
    status_str = "ok" if 200 <= status_code < 400 else "error"
    return Response(
        {"data": data, "message": message, "status": status_str},
        status=status_code,
    )

User = get_user_model()

class CheckAvailabilityView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, item):
        item = item.lower()

        if item == "username":
            username = request.data.get("username")
            if not username:
                return api_response(
                    data=None,
                    message="Missing username",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            exists = User.objects.filter(username=username).exists()

            if exists:
                return api_response(
                    data={"valid": 0},
                    message="User Exists",
                    status_code=status.HTTP_200_OK,
                )
            else:
                return api_response(
                    data={"valid": 1},
                    message="Username Can Be Used",
                    status_code=status.HTTP_200_OK,
                )

        elif item == "email":
            email = request.data.get("email")
            if not email:
                return api_response(
                    data=None,
                    message="Missing email",
                    status_code=status.HTTP_400_BAD_REQUEST,
                )

            qs = User.objects.filter(email=email)

            qs = qs.exclude(id=request.user.id)

            exists = qs.exists()

            if exists:
                return api_response(
                    data={"valid": 0},
                    message="Email Has Been Used",
                    status_code=status.HTTP_200_OK,
                )
            else:
                return api_response(
                    data={"valid": 1},
                    message="Email Can Be Used",
                    status_code=status.HTTP_200_OK,
                )

        else:
            return api_response(
                data=None,
                message="Invalid Checking Type",
                status_code=status.HTTP_400_BAD_REQUEST,
            )
