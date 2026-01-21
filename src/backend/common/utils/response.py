from django.http import JsonResponse


def success_response(data, message="", status_code=200):
    return JsonResponse(
        {
            "status": "success",
            "data": data,
            "message": message,
        },
        status=status_code,
    )


def error_response(message="", status_code=400):
    return JsonResponse(
        {
            "status": "faild",
            "message": message,
        },
        status=status_code,
    )
