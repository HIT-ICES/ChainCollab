import yaml
import subprocess
from jinja2 import Template
import time


def load_config(config_path):
    """加载配置文件"""
    with open(config_path, "r") as f:
        config = yaml.safe_load(f)
    return config


def generate_go_config(python_config, output_path):
    """根据 Python 配置生成适用于 Go 的配置文件"""
    go_config = {"queue": python_config["queue"], "database": python_config["database"]}

    # 写入 Go 配置文件
    with open(output_path, "w") as f:
        yaml.dump(go_config, f, default_flow_style=False)

    print(f"Go 配置文件已生成：{output_path}")


def generate_docker_compose(config, template_path, output_path):
    """根据配置生成 docker-compose.yml 文件"""
    # 读取模板文件
    with open(template_path, "r") as f:
        template_content = f.read()

    # 准备填充模板的变量
    # context = {
    #     "mysql_image": config["database"]["mysql"].get("image", "mysql:5.7"),
    #     "mysql_password": config["database"]["mysql"]["password"],
    #     "mysql_port": config["database"]["mysql"]["port"],
    #     "redis_image": config["database"]["redis"].get("image", "redis:latest"),
    #     "redis_port": config["database"]["redis"]["port"],
    #     "mode": config["mode"]
    # }

    context = {
        "mysql_image": config["database"]["mysql"].get("image", "mysql:5.7"),
        "mysql_password": config["database"]["mysql"]["password"],
        "mysql_port": config["database"]["mysql"]["port"],
        "mysql_dbname": config["database"]["mysql"]["dbname"],  # 新增
        "redis_image": config["database"]["redis"].get("image", "redis:latest"),
        "redis_port": config["database"]["redis"]["port"],
        "mode": config["mode"]
    }
    # 使用 Jinja2 渲染模板
    template = Template(template_content)
    rendered_content = template.render(context)

    # 将渲染后的内容写入 docker-compose.yml 文件
    with open(output_path, "w") as f:
        f.write(rendered_content)

    print(f"Docker Compose 文件已生成：{output_path}")


def start_docker_compose():
    """运行 docker-compose"""
    print("启动 Docker Compose...")
    subprocess.run(["docker-compose", "-f", "./temp/docker-compose.yml", "up", "-d"], check=True)
    # CHECK if mysql is prepared
    # wait 5 seconds
    time.sleep(10)

def down_docker_compose():
    """停止 docker-compose"""
    print("停止 Docker Compose...")
    subprocess.run(["docker-compose", "-f", "./temp/docker-compose.yml", "down"], check=True)


def start_go_service():
    """直接启动 Go 服务"""
    print("启动 Go 服务...")
    subprocess.run(["go", "run", "./cmd/server/main.go"], check=True)


def main():
    config_path = "./scripts/config.yaml"
    template_path = "./build/docker-compose-template.yml"
    output_docker_compose_path = "temp/docker-compose.yml"
    output_go_config_path = "config.yml"

    # 载入 Python 配置
    config = load_config(config_path)

    # 根据配置生成 Go 配置文件
    generate_go_config(config, output_go_config_path)

    # 根据配置生成 docker-compose.yml 文件
    generate_docker_compose(config, template_path, output_docker_compose_path)

    # 根据模式决定如何启动服务
    if config["mode"] == "prod":
        # 在生产模式下启动 Docker Compose
        start_docker_compose()
    elif config["mode"] == "dev":
        # 在开发模式下直接启动 Go 服务
        start_docker_compose()
        try:
            start_go_service()
        finally:
            down_docker_compose()
    else:
        raise ValueError("Invalid mode, must be 'dev' or 'prod'")
    


if __name__ == "__main__":
    main()