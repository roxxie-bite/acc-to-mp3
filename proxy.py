import socket, subprocess, os, logging, requests, threading
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
SOURCE_URL = os.environ.get("SOURCE_URL", "https://radiorecord.hostingradio.ru/phonk96.aacp")
BITRATE = os.environ.get("BITRATE", "128k")
PORT = int(os.environ.get("PORT", 8000))

_geo_cache = {}
_geo_lock = threading.Lock()

def get_country(ip):
    with _geo_lock:
        if ip in _geo_cache: return _geo_cache[ip]
    try:
        country = requests.get(f"http://ip-api.com/json/{ip}?fields=country", timeout=2).json().get("country", "Unknown")
    except: country = "Unknown"
    with _geo_lock: _geo_cache[ip] = country
    return country

def handle_client(conn, addr):
    ip = addr[0]
    country = get_country(ip)
    logging.info(f"[{datetime.now().strftime('%H:%M:%S')}] 🎧 CONNECT | IP: {ip} | Country: {country}")
    try:
        conn.recv(1024)  # drain request
        # 🔥 HTTP/1.0 + Connection: close — именно это ждёт FMOD
        conn.sendall(b"HTTP/1.0 200 OK\r\nContent-Type: audio/mpeg\r\nicy-name: CloudPhonk\r\nicy-br: 128\r\nicy-genre: Phonk\r\nConnection: close\r\n\r\n")
        proc = subprocess.Popen(['ffmpeg','-re','-timeout','30000000','-i',SOURCE_URL,'-codec:a','libmp3lame','-b:a',BITRATE,'-f','mp3','pipe:1'], stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=4096)
        while True:
            chunk = proc.stdout.read(4096)
            if not chunk: break
            conn.sendall(chunk)
    except Exception as e: logging.warning(f"Error: {e}")
    finally:
        conn.close()
        if 'proc' in locals(): proc.kill()

def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(('0.0.0.0', PORT))
    s.listen(5)
    logging.info(f"🚀 FMOD Proxy on :{PORT}")
    while True:
        conn, addr = s.accept()
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == '__main__': main()