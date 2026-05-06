#!/bin/bash
# FileDrop 部署脚本
set -e

CONTAINER_NAME="file-drop"
IMAGE_NAME="file-drop"
PORT=58085

echo "=== FileDrop 部署 ==="

# 构建镜像
echo ">>> 构建镜像..."
docker build -t $IMAGE_NAME .

# 停止旧容器
echo ">>> 停止旧容器..."
docker stop $CONTAINER_NAME 2>/dev/null || true
docker rm $CONTAINER_NAME 2>/dev/null || true

# 启动新容器
echo ">>> 启动新容器..."
docker run -d \
    --name $CONTAINER_NAME \
    --restart unless-stopped \
    -p 127.0.0.1:$PORT:5000 \
    -v /root/file-drop-data:/data \
    -e R2_ACCOUNT_ID="${R2_ACCOUNT_ID}" \
    -e R2_ACCESS_KEY_ID="${R2_ACCESS_KEY_ID}" \
    -e R2_ACCESS_KEY_SECRET="${R2_ACCESS_KEY_SECRET}" \
    -e R2_BUCKET="${R2_BUCKET:-steam-manifests}" \
    $IMAGE_NAME

echo ">>> 部署完成！容器端口: 127.0.0.1:$PORT"
echo ">>> 请确保 Cloudflare Tunnel 已配置路由到 http://localhost:$PORT"
