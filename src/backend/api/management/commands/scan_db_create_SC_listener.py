from django.core.management.base import BaseCommand
from api.management.commands.listeners.dmn_create_listener import InstanceCreatedAction
from api.management.commands.listeners.dmn_execute_listener import (
    DMNContentRequiredAction,
)
from api.models import BPMN
import threading
import logging

import websockets
import asyncio
import json
from concurrent.futures import ThreadPoolExecutor

# In-memory data structure to track events with created listeners
created_listeners = set()
executor = ThreadPoolExecutor()
ws_uri = "ws://localhost:5000/ws"  # 替换为你的 WebSocket 服务器地址


async def listen(executor, uri, listen_subscription_name, listen_action):
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
                await loop.run_in_executor(executor, listen_action, message)
            except websockets.ConnectionClosed:
                print("Connection closed")
                break


def listener_exists(event):
    # Check if the listener for the event already exists in the set
    return event in created_listeners


def scan_database():
    for bpmn in BPMN.objects.all():
        if bpmn.events:
            events = bpmn.events.split(
                ","
            )  # Assuming events are separated by semicolons
            chaincode_url = bpmn.firefly_url
            for event in events:
                chaincode_name = bpmn.chaincode.name
                event_listener_name = event + "-" + chaincode_name
                if not listener_exists(event_listener_name):
                    create_listener(chaincode_url, event, event_listener_name)


def create_listener(chaincode_url, event, event_listener_name):
    if event == "DMNContentRequired":
        listener_action = DMNContentRequiredAction(
            "http://127.0.0.1:5000/", chaincode_url=chaincode_url
        ).handle_read_dmn
    elif event == "InstanceCreated":
        listener_action = InstanceCreatedAction(
            core_url="http://127.0.0.1:5000/",
            chaincode_url=chaincode_url,
        ).handle_upload_dmn
    logging.info(f"Creating listener for event: {event}")
    asyncio.get_event_loop().run_until_complete(
        listen(
            executor=executor,
            uri=ws_uri,
            listen_subscription_name=event_listener_name,
            listen_action=listener_action,
        )
    )
    created_listeners.add(event)


class Command(BaseCommand):
    help = "Scans the database for updates"

    def handle(self, *args, **options):
        self.stdout.write("Scanning the database...")
        scan_database()
        self.stdout.write("Database scan complete.")
