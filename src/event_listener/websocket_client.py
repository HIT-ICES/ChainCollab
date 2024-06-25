import asyncio
from time import sleep
import requests
import websockets
import json
import threading
from concurrent.futures import ThreadPoolExecutor

core_url = "http://127.0.0.1:5000/"
chaincode_url = f"""{core_url}api/v1/namespaces/default/apis/event2-test/"""


async def listen(executor):
    uri = "ws://localhost:5000/ws"  # 替换为你的 WebSocket 服务器地址
    listen_subscription_name = "dmn_create2"
    async with websockets.connect(uri) as websocket:
        # 连接后发送一条消息
        message_to_send = {
            "type": "start",
            "name": listen_subscription_name,
            "namespace": "default",
            "autoack": True,
        }
        await websocket.send(json.dumps(message_to_send))
        print(f"Sent message: {message_to_send}")

        # 开始监听来自服务器的消息
        while True:
            try:
                message = await websocket.recv()
                print(f"Received message: {message}")
                # 在接收到消息后启动一个线程执行send_post_request
                loop = asyncio.get_event_loop()
                await loop.run_in_executor(executor, handle_message, message)
            except websockets.ConnectionClosed:
                print("Connection closed")
                break


def handle_message(message):
    print(f"Received message: {message}")
    # 将字符串转换为字典
    data = json.loads(message)
    eventContent = data.get("blockchainEvent").get("output")
    print("------------\n", eventContent)
    dmn_content = eventContent.get("DMNContent")
    Id = eventContent.get("ID")
    data_id = invoke_upload_data(dmn_content, Id)
    invoke_broadcast_data(data_id)
    # 如果不休眠2秒，broadcast未完成，query_data会返回None（还未传到IPFS）
    sleep(2)
    IPFS_cid = query_data(data_id)
    print(f"IPFS_cid: {IPFS_cid}")
    update_chaincode_cid(Id, IPFS_cid)


def invoke_upload_data(data_content, Id):
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


def invoke_broadcast_data(Id):
    # 目标URL
    url = f"""{core_url}api/v1/namespaces/default/messages/broadcast"""
    # Headers
    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(
        url, data=json.dumps({"data": [{"id": Id}]}), headers=headers
    )
    print(response.text)


def query_data(Id):
    # 目标URL
    url = f"""{core_url}api/v1/namespaces/default/data/{Id}"""
    response = requests.get(url)
    print(response.text)
    res_json = json.loads(response.text)
    return res_json.get("blob").get("public")


def update_chaincode_cid(id, cid):
    print(f"Updating chaincode with id: {id} and cid: {cid}")
    url = f"""{chaincode_url}invoke/UpdateCid"""
    request_body = {"input": {"id": id, "cid": cid}}
    json_data = json.dumps(request_body)
    headers = {
        "Content-Type": "application/json",
    }
    response = requests.post(url, data=json_data, headers=headers)
    print(response.text)


# 创建线程池执行器
executor = ThreadPoolExecutor()
# 运行 WebSocket 监听器
asyncio.get_event_loop().run_until_complete(listen(executor=executor))
