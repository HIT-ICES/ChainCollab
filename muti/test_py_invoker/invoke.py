import time
import fastapi
import json

import requests
from test_1000 import machineStr,additionalStr


res = requests.post(
    "http://127.0.0.1:5001/api/v1/namespaces/default/apis/StateChartEngine5/query/get_default_snapshot",
    json={
        "input": {
            "additionalContentStr": additionalStr,
            "machineDescriptionStr": machineStr,
        }
    },
)
print("get_default_snapshot", res.text)


snapshot = res.text
T1 = time.time()


res = requests.post(
    "http://127.0.0.1:5001/api/v1/namespaces/default/apis/StateChartEngine5/query/executeStateMachine",
    json={
        "input": {
            "additionalContentStr": additionalStr,
            "machineDescriptionStr": machineStr,
            "snapshotStr":snapshot,
            "eventStr": """{"type":"Send_Message_0j305jt_1"}"""
        }
    },
)
T2 = time.time()

print("--------------------------------")
print(res.text)

print('程序运行时间:%s毫秒' % ((T2 - T1)*1000))
