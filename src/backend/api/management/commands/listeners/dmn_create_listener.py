import asyncio
from time import sleep
import requests
import json
from concurrent.futures import ThreadPoolExecutor

from api.config import CURRENT_IP
from api.management.commands.listeners.dmn_execute_listener import listen


class InstanceCreatedAction:
    def __init__(self, core_url, chaincode_url, bpmn_id):
        self.core_url = core_url
        self.chaincode_url = chaincode_url
        self.bpmn_id = bpmn_id

    def handle_upload_dmn(self, message):
        print(f"Received message: {message}")
        # 将字符串转换为字典
        data = json.loads(message)
        eventContent = data.get("blockchainEvent").get("output")
        print("------------\n", eventContent)
        instance_id = eventContent.get("InstanceID")
        self.create_db_instance(instance_id=instance_id)

        for key, value in eventContent.items():
            if key == "InstanceID":
                continue
            dmn_content = value
            dmn_Id = key
            data_id = self.invoke_upload_data(
                dmn_content, instance_id + "@" + dmn_Id, core_url=self.core_url
            )
            self.invoke_broadcast_data(data_id)
            # 如果不休眠2秒，broadcast未完成，query_data会返回None（还未传到IPFS）
            sleep(2)
            IPFS_cid = self.query_data(data_id)
            print(f"IPFS_cid: {IPFS_cid}")
            self.update_chaincode_cid(
                cid=IPFS_cid, instanceId=instance_id, business_rule_id=dmn_Id
            )

    def invoke_upload_data(self, data_content, Id, core_url):
        # 目标URL
        url = f"""{core_url}api/v1/namespaces/default/data"""
        # 构造请求
        response = requests.post(
            url,
            files={"file": (Id + ".xml", data_content, "application/xml")},
            data={"autometa": "true"},
        )
        print(response.text)
        res_json = json.loads(response.text)
        data_id = res_json.get("id")
        return data_id

    def invoke_broadcast_data(self, Id):
        # 目标URL
        url = f"""{self.core_url}api/v1/namespaces/default/messages/broadcast"""
        # Headers
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(
            url, data=json.dumps({"data": [{"id": Id}]}), headers=headers
        )
        print(response.text)

    def query_data(self, Id):
        # 目标URL
        url = f"""{self.core_url}api/v1/namespaces/default/data/{Id}"""
        response = requests.get(url)
        print(response.text)
        res_json = json.loads(response.text)
        return res_json.get("blob").get("public")

    def update_chaincode_cid(self, cid, instanceId, business_rule_id):
        print(f"Updating chaincode with instanceId: {instanceId} and cid: {cid}")
        url = f"""{self.chaincode_url}/invoke/UpdateCID"""
        request_body = {
            "input": {
                "InstanceID": instanceId,
                "BusinessRuleID": business_rule_id,
                "cid": cid,
            }
        }
        json_data = json.dumps(request_body)
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(url, data=json_data, headers=headers)
        print(response.text)

    def create_db_instance(self, instance_id):
        print(f"Creating DB instance with instance_id: {instance_id}")
        url = f"http://{CURRENT_IP}:8000/api/v1/bpmns/{self.bpmn_id}/bpmn-instances"
        request_body = {"instance_chaincode_id": instance_id, "name": instance_id}
        json_data = json.dumps(request_body)
        headers = {
            "Content-Type": "application/json",
        }
        response = requests.post(url, data=json_data, headers=headers)
        # print(response.text)
        with open("instance_create_response.json", "w") as f:
            f.write(response.text)


if __name__ == "__main__":

    core_url = "http://127.0.0.1:5000/"
    chaincode_url = f"""{core_url}api/v1/namespaces/default/apis/Test12/"""
    ipfs_url = "http://127.0.0.1:10207/ipfs/"
    uri = "ws://localhost:5000/ws"  # 替换为你的 WebSocket 服务器地址
    listen_subscription_name = "instance_created_12"
    # 创建线程池执行器
    executor = ThreadPoolExecutor()
    # 运行 WebSocket 监听器
    asyncio.get_event_loop().run_until_complete(
        listen(
            executor=executor,
            uri=uri,
            listen_subscription_name=listen_subscription_name,
            listen_action=InstanceCreatedAction(
                core_url=core_url, chaincode_url=chaincode_url
            ).handle_upload_dmn,
        )
    )
