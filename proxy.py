import subprocess
import os
import logging
from flask import Flask, Response

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

SOURCE_URL = os.environ.get("SOURCE_URL", "https://radiorecord.hostingradio.ru/phonk96.aacp")
BITRATE = os.environ.get("BITRATE", "128k")
PORT = int(os.environ.get("PORT", 10000))

def stream_generator():
    # -timeout 30000000 = 30 сек (в микросекундах) чтобы ffmpeg не висел при обрыве
    command = [
        'ffmpeg', '-re', '-timeout', '30000000', '-i', SOURCE_URL,
        '-codec:a', 'libmp3lame', '-b:a', BITRATE,
        '-f', 'mp3', '-loglevel', 'error',
        'pipe:1'
    ]
    logging.info("🎬 FFmpeg stream started")
    proc = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, bufsize=8192)
    try:
        while True:
            chunk = proc.stdout.read(8192)
            if not chunk:
                break
            yield chunk
    finally:
        proc.kill()

@app.route('/stream.mp3')
def stream():
    return Response(
        stream_generator(),
        mimetype='audio/mpeg',
        headers={
            'Content-Type': 'audio/mpeg',
            'icy-name': 'Cloud Phonk',
            'icy-br': '128',
            'icy-url': SOURCE_URL,
            'icy-genre': 'Phonk',
            'Connection': 'close',  # FMOD стабильнее работает без keep-alive
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Pragma': 'no-cache',
            'Accept-Ranges': 'none',
            'Transfer-Encoding': 'chunked'  # явно указываем, что поток чанковый
        }
    )

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    logging.info(f"🚀 Proxy running on :{PORT}")
    app.run(host='0.0.0.0', port=PORT)