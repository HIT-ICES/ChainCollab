import asyncio
import requests
import websockets
import json
import threading


async def listen():
    uri = "ws://localhost:5000/ws"  # 替换为你的 WebSocket 服务器地址
    async with websockets.connect(uri) as websocket:
        # 连接后发送一条消息
        message_to_send = {
            "type": "start",
            "name": "DmnEvent",
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
                thread = threading.Thread(target=handle_message, args=(message,))
                thread.start()
            except websockets.ConnectionClosed:
                print("Connection closed")
                break


async def handle_message(message):
    print(f"Received message: {message}")
    # 将字符串转换为字典
    data = json.loads(message)
    eventContent = data.get("blockchainEvent").get("output")
    print("------------\n", eventContent)
    dmn_content = eventContent.get("DMNContent")
    Id = eventContent.get("ID")
    invoke_upload_data(dmn_content, Id)


def invoke_upload_data(data_content, Id):
    # 目标URL
    url = "http://127.0.0.1:5000/api/v1/namespaces/default/data"
    # 构造请求
    response = requests.post(
        url,
        files={"file": (Id + ".xml", data_content, "application/xml")},
        data={"autometa": "true"},
    )
    print(response.text)


# 运行 WebSocket 监听器
asyncio.get_event_loop().run_until_complete(listen())
