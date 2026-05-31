import subprocess
import os
import logging
from flask import Flask, Response, stream_with_context

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

# 🔧 Переменные окружения (Render подставит PORT автоматически)
SOURCE_URL = os.environ.get("SOURCE_URL", "https://radiorecord.hostingradio.ru/phonk96.aacp")
BITRATE = os.environ.get("BITRATE", "128k")
PORT = int(os.environ.get("PORT", 10000))

def transcode_stream():
    # -re читает поток в реальном времени (ОБЯЗАТЕЛЬНО для облака!)
    command = [
        'ffmpeg', '-re', '-i', SOURCE_URL,
        '-codec:a', 'libmp3lame', '-b:a', BITRATE,
        '-f', 'mp3', '-loglevel', 'error',
        'pipe:1'
    ]
    logging.info(f"🎬 Запуск транскодинга: {' '.join(command)}")
    
    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        bufsize=8192
    )
    
    try:
        while True:
            chunk = process.stdout.read(8192)
            if not chunk:
                break
            yield chunk
    finally:
        process.kill()

@app.route('/stream.mp3')
def stream():
    return Response(
        stream_with_context(transcode_stream()),
        mimetype='audio/mpeg',
        headers={'Cache-Control': 'no-cache, no-store, must-revalidate'}
    )

@app.route('/health')
def health():
    return "OK", 200

if __name__ == '__main__':
    logging.info(f"🚀 Radio Proxy запущен на порту {PORT}")
    logging.info(f"📡 Источник: {SOURCE_URL}")
    app.run(host='0.0.0.0', port=PORT)