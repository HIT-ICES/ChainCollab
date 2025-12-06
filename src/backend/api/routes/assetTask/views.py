# api/routes/assetTask/views.py

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from api.management.commands.listeners.asset_upload_listener import (
    AssetUploadRequiredAction,
)
from api.models import BPMN

CORE_URL = "http://127.0.0.1:5000/"


@csrf_exempt
def upload_asset(request):
    
    if request.method != "POST":
        return JsonResponse({"error": "only POST allowed"}, status=405)

    # -------- 1. 读取基础参数 --------
    instance_id = request.POST.get("instance_id")
    activity_id = request.POST.get("activity_id")
    func_name = request.POST.get("func_name")
    bpmn_id = request.POST.get("bpmn_id")
    identity = request.POST.get("identity")
    correct_url = request.POST.get("correct_url")
    file_obj = request.FILES.get("file")
    text_content = request.POST.get("content")

    if not instance_id or not activity_id or not func_name or not bpmn_id:
        return JsonResponse(
            {
                "error": "missing instance_id / activity_id / func_name / bpmn_id",
                "instance_id": instance_id,
                "activity_id": activity_id,
                "func_name": func_name,
                "bpmn_id": bpmn_id,
            },
            status=400,
        )

    # -------- 2. 根据 bpmn_id 计算 chaincode_url --------
    try:
        bpmn = BPMN.objects.get(id=bpmn_id)
    except BPMN.DoesNotExist:
        return JsonResponse({"error": f"bpmn {bpmn_id} not found"}, status=404)

    firefly_url = bpmn.firefly_url  
    if firefly_url.endswith("/api"):
        chaincode_url = firefly_url[:-4]  
    else:
        chaincode_url = firefly_url

    # -------- 3. 读取上传内容（优先文件，其次文本） --------
    if file_obj:
        content_bytes = file_obj.read()
        filename = file_obj.name
    elif text_content:
        content_bytes = text_content.encode("utf-8")
        filename = f"{activity_id}.txt"
    else:
        return JsonResponse({"error": "missing file or content"}, status=400)

    # 4. 调用 AssetUploadRequiredAction-------
    try:
        action = AssetUploadRequiredAction(
            core_url=CORE_URL,
            chaincode_url=chaincode_url,
        )
        action.process_uploaded_asset_bytes(
            instance_id=instance_id,
            activity_id=activity_id,
            func_name=func_name,
            content_bytes=content_bytes,
            filename=filename,
            identity = identity,
            correct_url=correct_url,
        )
        return JsonResponse({"status": "ok"})
    except Exception as e:
        print("[upload_asset] error:", e)
        return JsonResponse({"error": str(e)}, status=500)
