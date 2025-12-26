from rest_framework.response import Response


def api_response(data=None, message="OK", status_code=200):
    return Response(
        {
            "data": data,
            "message": message,
            "status_code": status_code,
        },
        status=status_code,
    )
