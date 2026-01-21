
import json
from functools import wraps
TEST_MODE_ON = False
REPORT_COUNT = 2
REPORT_NAME = f"report{REPORT_COUNT}.json"

# format 
# {
#     "test_name": "Describe the test setting",
#     "tests":[
#         {
#             "epoch": 1,
#             "Init_cost": 0.0,
#             "Join_cost": [0.0, 0.0, 0.0, 0.0, 0.0],
#             "Start_cost": 0.0,
#             "Activate_cost": 0.0,
#             "Firefly_cost": 0.0
#         }
#     ]
# }

# 装饰器实现记录接口用时
from time import time
def timeitwithname(name):
    def timeit(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            start = time()
            result = func(*args, **kwargs)
            cost_time = time() - start
            with open (REPORT_NAME, "r") as f:
                content = json.load(f)
            # parse and modify the content
            current_test = content["tests"]
            lastest_epoch = current_test[-1] if current_test else {
                "epoch": -1,
            }
            match name:
                case "Init":
                    # create a new epoch
                    current_test.append({
                        "epoch": lastest_epoch["epoch"] + 1,
                        "Init_cost": cost_time,
                        "Join_cost": [],
                        "Start_cost": 0.0,
                        "Activate_cost": 0.0,
                        "Firefly_cost": 0.0
                    })
                case "Join":
                    lastest_epoch["Join_cost"].append(cost_time)
                case "Start":
                    lastest_epoch["Start_cost"] = cost_time
                case "Activate":
                    lastest_epoch["Activate_cost"] = cost_time
                case "Firefly":
                    lastest_epoch["Firefly_cost"] = cost_time
            with open (REPORT_NAME, "w") as f:
                json.dump(content, f)
            return result
        if TEST_MODE_ON:
            return wrapper
        return func
    return timeit
