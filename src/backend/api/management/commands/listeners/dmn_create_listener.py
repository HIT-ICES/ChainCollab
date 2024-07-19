import asyncio
from time import sleep
import requests
import json
from concurrent.futures import ThreadPoolExecutor

from api.management.commands.listeners.dmn_execute_listener import listen


# async def listen(executor, uri, listen_subscription_name, listen_action):
#     async with websockets.connect(uri) as websocket:
#         # 连接后发送一条消息
#         message_to_send = {
#             "type": "start",
#             "name": listen_subscription_name,
#             "namespace": "default",
#             "autoack": True,
#         }
#         await websocket.send(json.dumps(message_to_send))
#         print(f"Sent message: {message_to_send}")

#         # 开始监听来自服务器的消息
#         while True:
#             try:
#                 message = await websocket.recv()
#                 print(f"Received message: {message}")
#                 # 在接收到消息后启动一个线程执行send_post_request
#                 loop = asyncio.get_event_loop()
#                 await loop.run_in_executor(executor, listen_action, message)
#             except websockets.ConnectionClosed:
#                 print("Connection closed")
#                 break


class InstanceCreatedAction:
    def __init__(self, core_url, chaincode_url):
        self.core_url = core_url
        self.chaincode_url = chaincode_url

    def handle_upload_dmn(self, message):
        print(f"Received message: {message}")
        # 将字符串转换为字典
        data = json.loads(message)
        eventContent = data.get("blockchainEvent").get("output")
        print("------------\n", eventContent)
        instance_id = eventContent.get("InstanceID")

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
