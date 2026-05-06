#!/usr/bin/env python3
"""
FileDrop - 扫码取件服务
后台上传文件到 R2，生成二维码，微信扫码直接下载
"""

import os
import uuid
import json
import logging
import mimetypes
from datetime import datetime

from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename

from storage import R2Storage

# 配置
R2_CONFIG = {
    'bucket_name': os.environ.get('R2_BUCKET', 'steam-manifests'),
    'endpoint_url': f"https://{os.environ.get('R2_ACCOUNT_ID', '9c2e8df25aa75d4399cac3ca1ed62e9d')}.r2.cloudflarestorage.com",
    'access_key_id': os.environ.get('R2_ACCESS_KEY_ID', ''),
    'access_key_secret': os.environ.get('R2_ACCESS_KEY_SECRET', ''),
}

# Flask app
app = Flask(__name__, static_folder='static', static_url_path='')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB 上传限制

# 日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# R2 存储
storage = R2Storage(R2_CONFIG)

# 文件记录持久化
DATA_FILE = os.environ.get('DATA_FILE', '/data/files.json')


def load_files():
    """加载文件列表"""
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            return []
    return []


def save_files(files):
    """保存文件列表"""
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump(files, f, ensure_ascii=False, indent=2)


# ============ API ============

@app.route('/api/upload', methods=['POST'])
def upload_file():
    """上传文件"""
    if 'file' not in request.files:
        return jsonify({'error': '没有选择文件'}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': '没有选择文件'}), 400

    # 保留原始文件名用于展示
    original_name = file.filename
    ext = os.path.splitext(original_name)[1] if '.' in original_name else ''
    file_id = str(uuid.uuid4())[:8]
    key = f"file-drop/{file_id}{ext}"

    # 猜测 content-type
    content_type = mimetypes.guess_type(original_name)[0] or 'application/octet-stream'

    # 获取文件大小（在上传前）
    file.seek(0, 2)
    file_size = file.tell()
    file.seek(0)

    # 上传到 R2
    result = storage.upload_file(file, key, content_type=content_type)
    if not result:
        return jsonify({'error': '上传失败'}), 500

    # 生成下载链接（预签名 URL，有效期 7 天）
    download_url = storage.generate_presigned_url(key, expires_in=7 * 24 * 3600)

    # 保存文件记录
    files = load_files()
    file_record = {
        'id': file_id,
        'name': original_name,
        'key': key,
        'size': file_size,
        'content_type': content_type,
        'download_url': download_url,
        'created_at': datetime.now().isoformat(),
    }
    files.append(file_record)
    save_files(files)

    logger.info(f"文件上传成功: {original_name} -> {key}")
    return jsonify(file_record)


@app.route('/api/files', methods=['GET'])
def list_files():
    """获取文件列表"""
    files = load_files()
    return jsonify(files)


@app.route('/api/files/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """删除文件"""
    files = load_files()
    file_record = next((f for f in files if f['id'] == file_id), None)
    if not file_record:
        return jsonify({'error': '文件不存在'}), 404

    # 从 R2 删除
    storage.delete_file(file_record['key'])

    # 从列表删除
    files = [f for f in files if f['id'] != file_id]
    save_files(files)

    logger.info(f"文件删除成功: {file_record['name']}")
    return jsonify({'success': True})


@app.route('/api/files/<file_id>/refresh', methods=['POST'])
def refresh_url(file_id):
    """刷新下载链接（预签名 URL 过期后用）"""
    files = load_files()
    for file_record in files:
        if file_record['id'] == file_id:
            download_url = storage.generate_presigned_url(file_record['key'], expires_in=7 * 24 * 3600)
            file_record['download_url'] = download_url
            save_files(files)
            return jsonify(file_record)

    return jsonify({'error': '文件不存在'}), 404


@app.route('/api/health', methods=['GET'])
def health():
    """健康检查"""
    return jsonify({'status': 'ok', 'storage': storage.is_available()})


# ============ 前端页面 ============

@app.route('/')
def index():
    """管理页面"""
    return send_from_directory('static', 'index.html')


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=False)
