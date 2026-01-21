#
# SPDX-License-Identifier: Apache-2.0
#
from django.apps import AppConfig

HOSTS_FILE = "/etc/hosts"


class ApiConfig(AppConfig):
    name = "apps.api"
    label = "api"
    _is_ready_called = True  # 添加一个标志

    def ready(self):
        if self._is_ready_called:
            return
        from apps.fabric.models import Node
        nodes = Node.objects.all()
        hosts = []
        for node in nodes:
            if node.type == "orderer":
                url = node.urls
                hosts.append(url.split(".", 1)[0] + "." + url.split(".", 2)[2])
            else:
                hosts.append(node.urls)
        print(hosts)
        print("add hosts to /etc/hosts")
        with open(HOSTS_FILE, "r+") as file:
            content = file.read()
            for host in hosts:
                host_entry = f"127.0.0.1 {host}"
                if host_entry in content:
                    print(f"Host entry {host} already exists in hosts file.")
                else:
                    print(f"Write host entry {host_entry} to /etc/hosts")
                    file.write(host_entry + "\n")
        self._is_ready_called = True
