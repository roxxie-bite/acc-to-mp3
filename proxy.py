#!/usr/bin/env python3
"""
ETS2 Radio Proxy — транскодирует AAC-потоки в MP3 для Euro Truck Simulator 2
Использует локальный ffmpeg из папки ./ffmpeg/bin/
"""

import subprocess
import sys
import os
from pathlib import Path
from flask import Flask, Response, stream_with_context

app = Flask(__name__)

# 🔧 НАСТРОЙКИ
SOURCE_URL = "https://radiorecord.hostingradio.ru/phonk96.aacp"  # исходный поток
BITRATE = "128k"  # битрейт MP3
LOCAL_PORT = 8080  # порт сервера

# 🎯 Путь к локальному ffmpeg
def get_ffmpeg_path():
    base_dir = Path(__file__).parent
    ffmpeg_dir = base_dir / "ffmpeg" / "bin"
    
    if not ffmpeg_dir.exists():
        raise RuntimeError(f"❌ Папка '{ffmpeg_dir}' не найдена!\nПоложи папку 'ffmpeg' рядом со скриптом.")
    
    if sys.platform == "win32":
        ffmpeg_exe = ffmpeg_dir / "ffmpeg.exe"
    else:
        ffmpeg_exe = ffmpeg_dir / "ffmpeg"
    
    if not ffmpeg_exe.exists():
        raise RuntimeError(f"❌ Файл '{ffmpeg_exe}' не найден!\nПроверь, что ffmpeg.exe лежит внутри ffmpeg/bin/")
    
    if sys.platform != "win32" and not os.access(ffmpeg_exe, os.X_OK):
        os.chmod(ffmpeg_exe, 0o755)
    
    return str(ffmpeg_exe)

FFMPEG_PATH = get_ffmpeg_path()

def transcode_stream():
    command = [
        FFMPEG_PATH,
        '-i', SOURCE_URL,
        '-codec:a', 'libmp3lame',
        '-b:a', BITRATE,
        '-f', 'mp3',
        '-loglevel', 'quiet',
        'pipe:1'
    ]
    
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
        headers={
            'Cache-Control': 'no-cache, no-store, must-revalidate',
            'Connection': 'keep-alive',
            'Content-Type': 'audio/mpeg'
        }
    )

@app.route('/')
def info():
    return f"""
    <h2>🎧 ETS2 Radio Proxy</h2>
    <p><b>Источник:</b> {SOURCE_URL}</p>
    <p><b>Локальный поток:</b> <a href="http://127.0.0.1:{LOCAL_PORT}/stream.mp3">http://127.0.0.1:{LOCAL_PORT}/stream.mp3</a></p>
    <p><b>FFmpeg:</b> {FFMPEG_PATH}</p>
    <p><b>Статус:</b> ✅ Работает</p>
    <hr>
    <p><small>Для ETS2 добавь в live_streams.sii:<br>
    <code>stream_data[]: "http://127.0.0.1:{LOCAL_PORT}/stream.mp3|Phonk Record Local|Phonk|Russian|128|0"</code></small></p>
    """

if __name__ == '__main__':
    print(f"🚀 ETS2 Radio Proxy")
    print(f"📦 FFmpeg: {FFMPEG_PATH}")
    print(f"📡 Источник: {SOURCE_URL}")
    print(f"🎧 Локальный поток: http://127.0.0.1:{LOCAL_PORT}/stream.mp3")
    print("💡 Добавь ссылку в live_streams.sii и запускай ETS2!")
    print("⚠️ Не закрывай это окно во время игры!\n")
    app.run(host='127.0.0.1', port=LOCAL_PORT, threaded=True)