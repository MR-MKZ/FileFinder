import os
import asyncio
from tqdm import tqdm
from fuzzywuzzy import fuzz
import time
import psutil
from flask import Flask, render_template, redirect, url_for, request, jsonify
from celery import Celery
import subprocess
import sys
import socket

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://localhost:80/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:80/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

def get_network_ip():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        
        sock.connect(("8.8.8.8", 80))
        
        ip_address = sock.getsockname()[0]
        
        sock.close()
        
        return ip_address
    except socket.error:
        return None


def find_similar_files(name, path, progress):
    results = []
    try:
        for root, dirs, files in os.walk(path):
            for entry in files + dirs:
                full_path = os.path.join(root, entry)
                similarity_ratio = fuzz.ratio(entry.lower(), name.lower())
                if similarity_ratio > 70: 
                    results.append((full_path, similarity_ratio, path))
                    progress.set_postfix({"Found": len(results)})
                    file = full_path.split('\\')[-1]
    except PermissionError:
        pass

    results.sort(key=lambda x: x[1], reverse=True)
    return [result for result in results]


async def search_drive(drive, filename, progress):
    return find_similar_files(filename, drive, progress)


async def search_all_drives(filename):
    drives = [drive.device for drive in psutil.disk_partitions()]
    results = []
    with tqdm(total=len(drives), desc="Searching drives", ncols=80, colour="green") as progress:
        tasks = []
        for drive in drives:
            tasks.append(search_drive(drive, filename, progress))
        for coro in asyncio.as_completed(tasks):
            sub_results = await coro
            results.extend(sub_results)
    return results


def format_size(size_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.2f} TB"


# Routes-------------------------------

@app.route('/')
def home():
    return render_template('index.html')


drive_sorted_result = {}


@app.route('/search', methods=['GET'])
def search():
    drive_sorted_result.clear()
    filename = request.args.get('search')

    start_time = time.time()
    results = asyncio.run(search_all_drives(filename))
    end_time = time.time()

    final_result = ""

    if not results:
        final_result = f"Could not find any similar files or folders for: {filename}\n"
        return jsonify(result=final_result)
    else:
        drives = []
        for result in results:
            if result[2] != [drive for drive in drives]:
                drives.append(result[2])
        result_id = 0
        for drive in drives:
            drive_sorted_result[drive] = []
            for result in results:
                if result[2] == drive:
                    file_size = os.path.getsize(result[0])
                    result_id += 1
                    drive_sorted_result[drive].append((result[0], result[1], format_size(file_size), result_id))
        print(f"\n\x1b[39mSearch completed in {end_time - start_time:.2f} seconds.")
        return jsonify(drive_sorted_result)


opened = 0


async def open_directory_process(result_id):
    global opened
    if opened < 1:
        for i in drive_sorted_result:
            for n in drive_sorted_result[i]:
                if int(result_id) == int(n[3]):
                    directory_path = n[0]

                    if sys.platform.startswith('darwin'):  # macOS
                        subprocess.run(['open', directory_path])
                        opened += 1
                        return 1
                    elif sys.platform.startswith('win32'):  # Windows
                        subprocess.run(['explorer', directory_path])
                        opened += 1
                        return 1
                    elif sys.platform.startswith('linux'):  # Linux
                        subprocess.run(['xdg-open', directory_path])
                        opened += 1
                        return 1
                    else:
                        return "Unsupported platform: " + sys.platform
    else:
        opened = 0


@app.route('/open/<result_id>')
def open_directory(result_id):

    open = asyncio.run(open_directory_process(result_id))
    if open == 1:
        return render_template('done.html', result_id=result_id)
    else:
        return redirect(url_for('home', result=open))


if __name__ == "__main__":
    try:
        try:
            ip = get_network_ip()
            if not ip:
                ip = '127.0.0.1'
                
            app.run(host=ip, port=80, debug=False)
        except EOFError:
            exit()
    except KeyboardInterrupt:
        exit()
