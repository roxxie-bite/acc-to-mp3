import socket
import subprocess
import os
import logging
import requests
import threading
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')

SOURCE_URL = os.environ.get("SOURCE_URL", "https://radiorecord.hostingradio.ru/phonk96.aacp")
BITRATE = os.environ.get("BITRATE", "128k")
PORT = int(os.environ.get("PORT", 10000))

_geo_cache = {}
_geo_lock = threading.Lock()

def get_country(ip):
    with _geo_lock:
        if ip in _geo_cache:
            return _geo_cache[ip]
    try:
        resp = requests.get(f'http://ip-api.com/json/{ip}?fields=country', timeout=2)
        country = resp.json().get('country', 'Unknown')
    except:
        country = 'Unknown'
    with _geo_lock:
        _geo_cache[ip] = country
    return country

def handle_client(conn, addr):
    ip = addr[0]
    country = get_country(ip)
    timestamp = datetime.now().strftime('%H:%M:%S')
    logging.info(f"[{timestamp}] 🎧 CONNECT | IP: {ip} | Country: {country}")
    
    # Минимальные заголовки, которые понимает FMOD
    http_response = (
        "HTTP/1.0 200 OK\r\n"
        "Content-Type: audio/mpeg\r\n"
        "icy-name: CloudPhonk\r\n"
        "icy-br: 128\r\n"
        "icy-genre: Phonk\r\n"
        "icy-pub: 1\r\n"
        "Connection: close\r\n"
        "Cache-Control: no-cache\r\n"
        "\r\n"
    ).encode('utf-8')
    
    try:
        conn.sendall(http_response)
        
        cmd = [
            'ffmpeg', '-re', '-timeout', '30000000', '-i', SOURCE_URL,
            '-codec:a', 'libmp3lame', '-b:a', BITRATE,
            '-f', 'mp3', '-loglevel', 'error', 'pipe:1'
        ]
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=4096)
        
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk:
                break
            conn.sendall(chunk)
    except Exception as e:
        logging.warning(f"Client disconnected: {e}")
    finally:
        conn.close()
        if 'proc' in locals():
            proc.kill()

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind(('0.0.0.0', PORT))
    server.listen(5)
    logging.info(f"🚀 TCP Proxy running on port {PORT} | Source: {SOURCE_URL}")
    
    while True:
        conn, addr = server.accept()
        thread = threading.Thread(target=handle_client, args=(conn, addr), daemon=True)
        thread.start()

if __name__ == '__main__':
    main()