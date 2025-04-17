import yaml
import subprocess
from jinja2 import Template
import time
import os


def load_config(config_path):
    with open(config_path, "r") as f:
        return yaml.safe_load(f)


def generate_go_app_config(config, output_path):
    app_config = config.get("app", {})
    with open(output_path, "w") as f:
        yaml.dump(app_config, f, default_flow_style=False)
    print(f"Go 配置文件已生成：{output_path}")


def generate_docker_compose(config, template_path, output_path):
    services = config.get("services", {})
    mysql = services.get("mysql", {})
    redis = services.get("redis", {})

    with open(template_path, "r") as f:
        template = Template(f.read())

    context = {
        "mysql_image": mysql.get("image", "mysql:5.7"),
        "mysql_password": mysql.get("password", "password"),
        "mysql_port": mysql.get("port", 3306),
        "mysql_dbname": mysql.get("dbname", "test"),

        "redis_image": redis.get("image", "redis:latest"),
        "redis_port": redis.get("port", 6379),
    }

    rendered = template.render(context)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w") as f:
        f.write(rendered)

    print(f"Docker Compose 文件已生成：{output_path}")


def start_docker_compose(compose_path):
    print("启动 Docker Compose...")
    subprocess.run(["docker-compose", "-f", compose_path, "up", "-d"], check=True)
    time.sleep(10)


def down_docker_compose(compose_path):
    print("停止 Docker Compose...")
    subprocess.run(["docker-compose", "-f", compose_path, "down"], check=True)


def start_go_service():
    print("启动 Go 服务...")
    subprocess.run(["go", "run", "./cmd/server/main.go"], check=True)


def main():
    config_path = "./scripts/config.yaml"
    template_path = "./build/docker-compose-template.yml"
    compose_output = "./temp/docker-compose.yml"
    app_config_output = "./config.yml"

    config = load_config(config_path)
    mode = config.get("system", {}).get("mode", "dev")

    generate_go_app_config(config, app_config_output)
    generate_docker_compose(config, template_path, compose_output)

    if mode == "prod":
        start_docker_compose(compose_output)
    elif mode == "dev":
        start_docker_compose(compose_output)
        try:
            start_go_service()
        finally:
            # pass
            down_docker_compose(compose_output)
    else:
        raise ValueError("Invalid mode, must be 'dev' or 'prod'")


if __name__ == "__main__":
    main()
