from subprocess import Popen, call
import subprocess
import traceback
from api.config import CELLO_HOME, FABRIC_CONFIG, FABRIC_TOOL
import yaml
import os


class Firefly_cli:
    def __init__(self, filepath=CELLO_HOME):
        self.filepath = filepath
        self.ff_path = os.path.expanduser("ff")
        self.firefly_config_path = os.path.expanduser("~/.firefly/stacks/")

    def init(self, firefly_name, channel_name, firefly_chaincode_name, ccp_files_path):
        try:
            # proxy_command = "export http_proxy=172.24.128.1:7890;export https_proxy=172.24.128.1:7890"
            # proxy_command = "export http_proxy=172.29.240.1:7890;export https_proxy=172.29.240.1:7890"
            manifest_file_path=FABRIC_CONFIG+"/manifest.json"
            command = [
                self.ff_path,
                "init fabric",
                firefly_name,
                "-m",
                manifest_file_path
            ]
            for ccp_path in ccp_files_path:
                command.append(f"""--ccp {ccp_path}""")
                command.append(f"""--msp {CELLO_HOME}""")
            command.append(f"""--channel {channel_name}""")
            command.append(f"""--chaincode {firefly_chaincode_name}""")
            command = " ".join(command)
            print(command)
            # output = call(proxy_command + ";" + command, shell=True)
            output = call(command, shell=True)
            print("Command Output:")
            # print(output)
            if output != 0:
                raise Exception("ff iniy command execute fail")
            firefly_stack_path = self.firefly_config_path + firefly_name
            # 读取YAML文件
            with open(firefly_stack_path + "/docker-compose.override.yml", "r") as file:
                data = yaml.safe_load(file)
            # 添加配置
            data["networks"] = {"default": {"name": "cello-net", "external": True}}
            # 将修改后的数据写回文件
            with open(firefly_stack_path + "/docker-compose.override.yml", "w") as file:
                yaml.dump(data, file)
        except Exception as e:
            traceback.print_exc(e)
            err_msg = "firefly init fail for {}!".format(e)
            raise Exception(err_msg)

    def start(self, firefly_name):
        try:
            command = [
                self.ff_path,
                "start",
                firefly_name,
                "--verbose",
                "--no-rollback",
            ]
            p = Popen(command)
            p.wait()
        except Exception as e:
            traceback.print_exc(e)
            err_msg = "firefly start fail for {}!".format(e)
            raise Exception(err_msg)

    def remove(self, firefly_name):
        try:
            command = [
                self.ff_path,
                "remove",
                firefly_name,
            ]
            process = Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            # 发送 "y" 给子进程的标准输入
            process.communicate(b"y\n")

            # 等待命令完成
            process.wait()
            # 打印标准输出

            print("remove ff_stack done")
        except Exception as e:
            traceback.print_exc(e)
            err_msg = "firefly start fail for {}!".format(e)
            raise Exception(err_msg)
