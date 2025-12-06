import json
from time import sleep
import time

import requests

from ..myRedis import setKV, readKV


class AssetUploadRequiredAction:
    """
    资产任务链下处理工具类：
    - handle_asset_upload：收到链上 AssetUploadRequired 事件时调用（记录/打印任务）
    - process_uploaded_asset_bytes：前端上传资产内容后调用（IPFS + Oracle + Continue）
    """

    def __init__(self, core_url: str, chaincode_url: str):
        # core_url 例如: "http://127.0.0.1:5000/"
        # chaincode_url 例如: http://127.0.0.1:5000/api/v1/namespaces/default/apis/YourBPMN
        self.core_url = core_url.rstrip("/") + "/"
        self.chaincode_url = chaincode_url.rstrip("/")
       
    # ==================== 1. 收到链上事件时调用 ====================
    def handle_asset_upload(self, message: str):
        """
        被 WebSocket 监听器调用：
        收到 AssetUploadRequired 事件后，把 instanceId / ActivityID / Func 记录下来。
        """
        print(f"[AssetUploadRequiredAction] Received message: {message}")
        data = json.loads(message)
        event_content = data.get("blockchainEvent", {}).get("output", {}) or {}

        instance_id = event_content.get("InstanceID")
        activity_id = event_content.get("ActivityID")
        func_name = event_content.get("Func")

        if not instance_id or not activity_id or not func_name:
            print("[AssetUploadRequiredAction] Missing fields in event output")
            return

        print(
            f"[AssetUploadRequiredAction] instance_id={instance_id}, "
            f"activity_id={activity_id}, func={func_name}"
        )

        # 可选：用 Redis 记录一个「待处理资产上传任务」
        try:
            task_key = f"asset_upload_task:{instance_id}:{activity_id}"
            task_value = json.dumps(
                {
                    "instance_id": instance_id,
                    "activity_id": activity_id,
                    "func_name": func_name,
                    "status": "PENDING",
                    "created_at": int(time.time() * 1000),
                }
            )
            setKV(task_key, task_value)
            print(f"[AssetUploadRequiredAction] Saved pending task: {task_key}")
        except Exception as e:
            print(f"[AssetUploadRequiredAction] Failed to save task to Redis: {e}")

    # ==================== 2. 前端上传资产内容后调用 ====================
    def process_uploaded_asset_bytes(
        self,
        instance_id: str,
        activity_id: str,
        func_name: str,
        content_bytes: bytes,
        filename: str,
        identity: str,
        correct_url:str,
    ):
        """
        通用处理：接收任意二进制内容 + 文件名
        → FireFly /data → broadcast → query 得到 CID
        → Oracle.SetDataItem(instanceId, activityId, cid)
        → 调 BPMN 链码的 Continue 函数（如 Activity_0i3c0p3_Continue）
        """

        # 1. 上传到 FireFly /data
        data_id = self._invoke_upload_data(
            data_content=content_bytes,
            file_name=filename,
            object_id=f"{instance_id}@{activity_id}",
        )

        # 2. 广播并查询 CID
        self._invoke_broadcast_data(data_id)
        sleep(2)  # 和 DMN 一样，等 FireFly 写好
        cid = self._query_data(data_id)
        print(f"[AssetUploadRequiredAction] IPFS CID: {cid}")

         # 3. 写入 BPMN 链码的 URLdatastorm：SetURLData(instanceID, key=activityID, value=cid)
        self._update_url_cid(cid=cid, instance_id=instance_id, activity_id=activity_id)
        time.sleep(2)
        # 4. 调 BPMN 链码的 Continue 函数（如 Activity_0i3c0p3_Continue）
        self._invoke_asset_continue(instance_id=instance_id, func_name=func_name,identity=identity,correct_url=correct_url)

        # 5. 可选：更新 Redis 任务状态
        try:
            task_key = f"asset_upload_task:{instance_id}:{activity_id}"
            task_json = readKV(task_key)
            if task_json:
                task_value = json.loads(task_json)
            else:
                task_value = {}
            task_value["status"] = "DONE"
            task_value["cid"] = cid
            setKV(task_key, json.dumps(task_value))
        except Exception:
            pass

    # ==================== FireFly / Oracle / BPMN 工具函数 ====================

    def _invoke_upload_data(self, data_content: bytes, file_name: str, object_id: str) -> str:
        url = f"{self.core_url}api/v1/namespaces/default/data"
        files = {"file": (file_name, data_content)}
        data = {"autometa": "true", "id": object_id}
        resp = requests.post(url, files=files, data=data)
        print("[Asset] upload data resp:", resp.text)
        res_json = resp.json()
        return res_json.get("id")

    def _invoke_broadcast_data(self, data_id: str):
        url = f"{self.core_url}api/v1/namespaces/default/messages/broadcast"
        headers = {"Content-Type": "application/json"}
        body = {"data": [{"id": data_id}]}
        resp = requests.post(url, data=json.dumps(body), headers=headers)
        print("[Asset] broadcast data resp:", resp.text)

    def _query_data(self, data_id: str) -> str:
        url = f"{self.core_url}api/v1/namespaces/default/data/{data_id}"
        resp = requests.get(url)
        print("[Asset] query data resp:", resp.text)
        res_json = resp.json()
        # FireFly 返回结构和 DMN 一样：blob.public 是 CID
        return res_json.get("blob", {}).get("public")

    def _update_url_cid(self, cid: str, instance_id: str, activity_id: str):
        print(f"[Asset] Write CID to URLdatastorm: instance={instance_id}, key={activity_id}, cid={cid}")
    
        url = f"{self.chaincode_url}/invoke/SetURLData"
    
        # 🔴 这里结构要跟 _invoke_asset_continue 一模一样，只是多了 key 和 value
        body = {
            "input": {
                "InstanceID": instance_id,          # 名字必须跟 FFI 里的完全一致
                "key": activity_id,
                "value": cid,
            }
        }
    
        resp = requests.post(
            url,
            data=json.dumps(body),                 # 和 Continue 一样，用 data + dumps
            headers={"Content-Type": "application/json"},
        )
        print("[Asset] update url resp:", resp.text)



    def _invoke_asset_continue(self, instance_id: str, func_name: str,identity:str,correct_url:str):
        """
        调 BPMN 合约的 Continue 函数，例如 Activity_0i3c0p3_Continue
        """
        body = {
        "input": {
            "InstanceID": instance_id,
        },
         "key": identity,
        }
        print(func_name)
        print(correct_url)
        try:
            resp = requests.post(
                correct_url,
                data=json.dumps(body),
                headers={"Content-Type": "application/json"},
            )
            print("[Asset] continue resp:", resp.text)
            return resp
        except Exception as e:
            print("[Asset] error calling continue:", e)
            return None
