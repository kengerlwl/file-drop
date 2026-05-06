#!/usr/bin/env python3
"""
Cloudflare R2 存储模块（简化版，参考 SteamHub）
"""

import logging
from typing import Optional, BinaryIO

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


class R2Storage:
    """Cloudflare R2 存储客户端"""

    def __init__(self, config: dict):
        self.client = None
        self.bucket_name = None

        try:
            self.bucket_name = config.get('bucket_name', 'file-drop')
            endpoint_url = config.get('endpoint_url')

            self.client = boto3.client(
                's3',
                endpoint_url=endpoint_url,
                aws_access_key_id=config.get('access_key_id'),
                aws_secret_access_key=config.get('access_key_secret'),
                config=Config(
                    signature_version='s3v4',
                    retries={'max_attempts': 3}
                )
            )
            logger.info(f"R2 存储初始化成功，Bucket: {self.bucket_name}")
        except Exception as e:
            logger.error(f"R2 存储初始化失败: {e}")

    def is_available(self) -> bool:
        return self.client is not None

    def upload_file(self, file_obj: BinaryIO, key: str, content_type: str = 'application/octet-stream') -> Optional[str]:
        """上传文件到 R2"""
        if not self.is_available():
            return None

        try:
            self.client.upload_fileobj(
                file_obj,
                self.bucket_name,
                key,
                ExtraArgs={'ContentType': content_type}
            )
            logger.info(f"文件上传成功: {key}")
            return key
        except ClientError as e:
            logger.error(f"文件上传失败: {e}")
            return None

    def delete_file(self, key: str) -> bool:
        """删除文件"""
        if not self.is_available():
            return False

        try:
            self.client.delete_object(Bucket=self.bucket_name, Key=key)
            logger.info(f"文件删除成功: {key}")
            return True
        except ClientError as e:
            logger.error(f"文件删除失败: {e}")
            return False

    def generate_presigned_url(self, key: str, expires_in: int = 3600) -> Optional[str]:
        """生成预签名下载 URL"""
        if not self.is_available():
            return None

        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket_name,
                    'Key': key,
                },
                ExpiresIn=expires_in
            )
            return url
        except ClientError as e:
            logger.error(f"生成预签名 URL 失败: {e}")
            return None
