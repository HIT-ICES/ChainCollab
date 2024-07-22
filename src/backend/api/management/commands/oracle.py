from django.core.management.base import BaseCommand
from api.management.commands.listeners.dmn_create_listener import InstanceCreatedAction
from api.management.commands.listeners.dmn_execute_listener import (
    DMNContentRequiredAction,
)
from api.models import BPMN
import websockets
import asyncio
from asgiref.sync import sync_to_async
import json
from concurrent.futures import ThreadPoolExecutor

# In-memory data structure to track events with created listeners
created_listeners = set()
executor = ThreadPoolExecutor()
ws_uri = "ws://localhost:5000/ws"  # 替换为你的 WebSocket 服务器地址


async def listener_task(chaincode_url, event_type, subscription_name, bpmn_id):
    async with websockets.connect(ws_uri) as websocket:
        # 连接后发送一条消息
        message_to_send = {
            "type": "start",
            "name": subscription_name,
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
                match event_type:
                    case "DMNContentRequired":
                        try:
                            DMNContentRequiredAction(
                                "http://127.0.0.1:5000/", chaincode_url=chaincode_url
                            ).handle_read_dmn(message)
                        except Exception as e:
                            print(e)
                    case "InstanceCreated":
                        try:
                            InstanceCreatedAction(
                                core_url="http://127.0.0.1:5000/",
                                chaincode_url=chaincode_url,
                                bpmn_id=bpmn_id,
                            ).handle_upload_dmn(message)
                        except Exception as e:
                            print(e)
            except websockets.ConnectionClosed:
                print("Connection closed")
                break


# namedTuple
from collections import namedtuple

TaskItem = namedtuple("TaskItem", ["task_id", "chaincode_url", "event_type", "bpmn_id"])
taskId2ref = dict()

taskList: list[TaskItem] = []


@sync_to_async
def get_all_bpmns():
    return [
        {
            "events": bpmn.events,
            "chaincode_name": bpmn.chaincode.name,
            "firefly_url": bpmn.firefly_url[:-4],
            "bpmn_id": bpmn.id,
        }
        for bpmn in BPMN.objects.all()
        if bpmn.events is not None
    ]


async def db_scanner():
    while True:
        bpmns = await get_all_bpmns()
        for bpmn in bpmns:
            if bpmn["events"]:
                events = bpmn["events"].split(
                    ","
                )  # Assuming events are separated by semicolons
                chaincode_url = bpmn["firefly_url"]
                for event in events:
                    chaincode_name = bpmn["chaincode_name"]
                    event_listener_name = event + "-" + chaincode_name
                    newTask = TaskItem(
                        task_id=event_listener_name,
                        chaincode_url=chaincode_url,
                        event_type=event,
                        bpmn_id=bpmn["bpmn_id"],
                    )
                    if newTask not in taskList:
                        taskList.append(newTask)
        await asyncio.sleep(5)
    # Remove TODO


async def task_manager():
    event_loop = asyncio.get_event_loop()
    while True:
        # get all tasks from event_loop
        for task in taskList:
            if task.task_id not in taskId2ref:
                taskId2ref[task.task_id] = event_loop.create_task(
                    listener_task(
                        chaincode_url=task.chaincode_url,
                        event_type=task.event_type,
                        subscription_name=task.task_id,
                        bpmn_id=task.bpmn_id,
                    )
                )
        await asyncio.sleep(5)


async def main():
    db_scanner_task = asyncio.create_task(db_scanner())
    task_manager_task = asyncio.create_task(task_manager())
    await asyncio.gather(db_scanner_task, task_manager_task)


class Command(BaseCommand):
    help = "Scans the database for updates"

    def handle(self, *args, **options):
        self.stdout.write("Scanning the database...")
        asyncio.run(main())
        self.stdout.write("Database scan complete.")
