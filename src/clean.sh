#!/bin/bash

# Remove Storage

echo "Remove Storage"

sudo chmod -R 777 ./agent/docker-rest-agent/CA_related/storage/fabric-ca-servers
sudo chmod -R 777 ./agent/docker-rest-agent/storage
rm -rf ./agent/docker-rest-agent/storage/*

echo "Remove Fabric CA storage"

sudo chmod -R 777 ./agent/docker-rest-agent/CA_related/storage/fabric-ca-servers
rm -rf ./agent/docker-rest-agent/CA_related/storage/fabric-ca-servers/*

echo "Remove Ethereum storage"

sudo chmod -R 777 ./agent/docker-rest-agent/eth/storage/servers
rm -rf ./agent/docker-rest-agent/eth/storage/servers/*

# Remove opt/cello

echo "Remove opt/cello"

rm -rf ./backend/opt/cello/*

# Remove opt/chaincode
echo "Remove opt/chaincode"
rm -rf ./backend/opt/chaincode/*

# Remove pgdata


echo "Remove pgdata"
sudo chmod -R 777 ./backend/pgdata
rm -rf ./backend/pgdata/*

# rm -rf /home/logres/LoLeido/cello/src/backend/opt/chaincode/*

echo "Remove py migrations"
find ./backend/api/migrations -type f -name '*_auto_*.py' -exec rm -f {} \;

# Remove Firefly
echo "Remove Firefly"
if command -v ff >/dev/null 2>&1; then
  ff list | grep 'cello_' | xargs -r -I{} sh -c "echo 'y' | ff remove {}" || true
else
  echo "ff not found, skip Firefly cleanup"
fi

# Remove Docker Container
#!/bin/bash

# 停止和删除以cello.com、edu.cn、tech.cn或org.com结尾的Docker容器，以及以太坊节点容器
while read -r container_name; do
    [ -n "$container_name" ] || continue
    echo "Stopping and removing container: $container_name"
    docker stop "$container_name" >/dev/null 2>&1 || true
    docker rm "$container_name" >/dev/null 2>&1 || true
done < <(docker ps -a --format "{{.Names}}" | grep -E 'com$|edu.cn$|tech.cn$|org.com$|geth|ethereum' || true)

# 移除 dev开头的image
while read -r image_name; do
    [ -n "$image_name" ] || continue
    echo "Removing image: $image_name"
    docker rmi "$image_name" >/dev/null 2>&1 || true
done < <(docker images --format "{{.Repository}}" | grep '^dev' || true)
# docker container prune -f
# docker volume prune -f

# Remove DB
echo "Remove DB"
docker stop cello-postgres >/dev/null 2>&1 || true
docker rm cello-postgres >/dev/null 2>&1 || true

echo "Finished cleaning"
