import subprocess
import os
import logging
import requests
import threading
from flask import Flask, Response, request

app = Flask(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

# 🔧 Конфиг из переменных окружения
SOURCE_URL = os.environ.get("SOURCE_URL", "https://radiorecord.hostingradio.ru/phonk96.aacp")
BITRATE = os.environ.get("BITRATE", "128k")
PORT = int(os.environ.get("PORT", 10000))

# 🌍 Real IP & GeoIP Logic
def get_real_ip():
    # Render/Cloudflare/Nginx передают реальный IP в заголовке X-Forwarded-For
    forwarded = request.headers.get('X-Forwarded-For')
    if forwarded:
        return forwarded.split(',')[0].strip()
    return request.headers.get('X-Real-IP', request.remote_addr)

_geo_cache = {}
_geo_lock = threading.Lock()

def get_country_by_ip(ip):
    # Проверка кэша
    with _geo_lock:
        if ip in _geo_cache:
            return _geo_cache[ip]
    
    try:
        # Бесплатный API без ключа (~45 запросов/мин)
        resp = requests.get(f'http://ip-api.com/json/{ip}?fields=country', timeout=3)
        data = resp.json()
        country = data.get('country', 'Unknown')
    except Exception as e:
        logging.warning(f"GeoIP lookup failed for {ip}: {e}")
        country = 'Unknown'
        
    with _geo_lock:
        _geo_cache[ip] = country
    return country

# 🎵 FFmpeg Streaming Generator
def stream_generator():
    command = [
        'ffmpeg', '-re', '-timeout', '30000000', '-i', SOURCE_URL,
        '-codec:a', 'libmp3lame', '-b:a', BITRATE,
        '-f', 'mp3', '-loglevel', 'error',
        'pipe:1'
    ]
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=8192)
    try:
        while True:
            chunk = proc.stdout.read(8192)
            if not chunk:
                break
            yield chunk
    finally:
        proc.kill()

# 📡 Endpoints
@app.route('/stream.mp3')
def stream():
    client_ip = get_real_ip()
    country = get_country_by_ip(client_ip)
    logging.info(f"🎧 Stream requested | IP: {client_ip} | Country: {country}")
    
    return Response(
        stream_generator(),
        mimetype='audio/mpeg',
        headers={
            'Content-Type': 'audio/mpeg',
            'icy-name': 'Cloud Phonk',
            'icy-br': '128',
            'icy-genre': 'Phonk',
            'Connection': 'close',
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache'
        }
    )

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    logging.info(f"🚀 Radio Proxy running on port {PORT}")
    logging.info(f"📡 Source: {SOURCE_URL}")
    app.run(host='0.0.0.0', port=PORT)