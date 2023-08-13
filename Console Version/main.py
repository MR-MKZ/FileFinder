import os
import asyncio
from tqdm import tqdm
from fuzzywuzzy import fuzz
import time
import platform
from plyer import notification
import psutil
from colorama import Fore, Style
from flask import Flask, render_template, redirect, url_for, request, jsonify
from celery import Celery
import random

app = Flask(__name__)
app.config['CELERY_BROKER_URL'] = 'redis://localhost:80/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:80/0'
celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)


def progress_bar(current, total, prefix='', suffix='', length=30, fill='=', print_end='\r'):
    percent = current / total
    filled_length = int(length * current // total)
    bar = fill * filled_length + ' ' * (length - filled_length)

    # Rainbow color effect
    colors = [Fore.RED, Fore.YELLOW, Fore.GREEN, Fore.CYAN, Fore.BLUE, Fore.MAGENTA]
    color_index = int((percent * len(colors))) % len(colors)
    bar = colors[color_index] + bar + Style.RESET_ALL

    print(f'\r{prefix} [{bar}] {percent:.1%} {suffix}', end=print_end)


def find_similar_files(name, path, progress):
    results = []
    try:
        for root, dirs, files in os.walk(path):
            for entry in files + dirs:
                full_path = os.path.join(root, entry)
                similarity_ratio = fuzz.ratio(entry.lower(), name.lower())
                if similarity_ratio > 70:  # Adjust the threshold as needed
                    results.append((full_path, similarity_ratio, path))
                    # progress_bar(1, len(results), prefix='Found:', suffix=str(len(results)))
                    progress.set_postfix({"Found": len(results)})
                    file = full_path.split('\\')[-1]
                    # print(f"Searching: {full_path}", end="\r")
    except PermissionError:
        pass

    # Sort the results based on similarity ratio (higher ratio first)
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


def clear_console():
    if platform.system() == "Windows":
        os.system("cls")
    else:
        os.system("clear")


async def main():
    filename = input("Enter the name of the file to search: ")
    clear_console()
    print(f"Searching for similar files and folders: {filename}\n")

    start_time = time.time()
    results = await search_all_drives(filename)
    end_time = time.time()

    clear_console()

    if not results:
        print(f"Could not find any similar files or folders for: {filename}\n")
    else:
        print(f"Found {len(results)} similar files or folders for: {filename}\n")
        drives = []
        for result in results:
            if result[2] != [drive for drive in drives]:
                drives.append(result[2])
        drive_sorted_result = {}
        for drive in drives:
            drive_sorted_result[drive] = []
            for result in results:
                if result[2] == drive:
                    file_size = os.path.getsize(result[0])
                    drive_sorted_result[drive].append((result[0], result[1], format_size(file_size)))
                    print(len(drive_sorted_result[drive]), end="\r")

        for drive in drive_sorted_result:
            rank = 0
            print(Fore.YELLOW + f"Founded results in drive " + Fore.RED + drive + Fore.WHITE + " :" + Fore.GREEN)
            for result in drive_sorted_result[drive]:
                rank += 1
                print(f"{rank} - Path: \x1b[36m{result[0]}\x1b[32m - ratio: {result[1]} - Size: {result[2]}")

    print(f"\n\x1b[39mSearch completed in {end_time - start_time:.2f} seconds.")

    # Send desktop notification
    notification_title = "Search Complete"
    notification_message = f"Search for '{filename}' completed. Found {len(results)} similar files or folders."
    notification.notify(title=notification_title, message=notification_message)


async def run_event_loop():
    loop = asyncio.get_event_loop()
    loop.create_task(app.run(host='127.0.0.1', port=80, debug=True))

    await loop.run_forever()


# Tasks-------------------------

# error num 10 : task not found !
# status 0: task cancelled
# status 1: task done 
# status 2: task pending  


# Dictionary to store tasks with their IDs
task_dict = {}

done_tasks = {}

cancel_tasks = []

destroy_tasks = []

loop = asyncio.get_event_loop()


# Function to add a new task
async def create_search_task(task_id, filename):
    async def search_main_operation(filename):
        start_time = time.time()
        results = await search_all_drives(filename)
        end_time = time.time()

        print(results)

        final_result = ""

        if not results:
            final_result = f"Could not find any similar files or folders for: {filename}\n"
            return jsonify(result=final_result)
        else:
            drives = []
            for result in results:
                if result[2] != [drive for drive in drives]:
                    drives.append(result[2])
            drive_sorted_result = {}
            for drive in drives:
                drive_sorted_result[drive] = []
                for result in results:
                    if result[2] == drive:
                        file_size = os.path.getsize(result[0])
                        drive_sorted_result[drive].append((result[0], result[1], format_size(file_size)))
            print(drive_sorted_result)

        # Remove the task from the dictionary after completion
        done_tasks[task_id] = drive_sorted_result
        del task_dict[task_id]

    # Schedule the task and store it in the task dictionary
    task = asyncio.ensure_future(search_main_operation(filename=filename))
    # task.add_done_callback(lambda t: print(f"Task {task_id} destroyed") and destroy_tasks.append(task_id))
    print(done_tasks)
    print(task_dict)
    print(destroy_tasks)
    task_dict[task_id] = task


# Fuction to get task status
def get_task_status(task_id):
    if task_id in task_dict:
        task = task_dict[str(task_id)]
        if task.done():
            return 1
        elif task.cancelled():
            return 0
        else:
            return 2
    else:
        task = task_dict[str(task_id)]
        print(task.done())
        return 10


# Function to cancel a task
def cancel_search_task(task_id):
    if task_id in task_dict:
        task = task_dict.pop(task_id)
        task.cancel()
        cancel_tasks.append(task_id)
        return 0
    else:
        return 10


# Cancel any remaining tasks
for task_id, task in task_dict.items():
    cancel_search_task(task_id)
    # task.cancel()
    # print(f"Task {task_id} canceled")
    # cancel_tasks.append(task_id)

# Close the event loop
loop.close()


# Routes-------------------------------

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/search', methods=['POST'])
def search():
    filename = request.form.get('search')

    task_id = str(random.randint(0, 999))
    # print(task_id)
    asyncio.run(create_search_task(task_id, filename))
    print(task_id)

    return str(task_id), 202


@app.route('/task_status/<task_id>', methods=['GET', 'POST'])
def task_status(task_id):
    task = get_task_status(task_id)

    if task == 0:
        return jsonify(status="cancelled")
    elif task == 1:
        result = task_dict[str(task_id)]
        print(result)
        return jsonify({
            "status": "done",
        })
    elif task == 2:
        return jsonify(status="pending")
    elif task == 10:
        return jsonify(status="not_found")

@app.route("/cancel_task/<task_id>")
def cancel_task(task_id):
    task = cancel_search_task(task_id)

    print(task)

    return jsonify(task)


@app.route('/tasks', methods=['GET', 'POST'])
def all_tasks():
    tasks_count = len(task_dict)

    result = {
        "count": tasks_count,
        "tasks_dict": task_dict,
        "done_tasks": done_tasks,
        "destroy_tasks": destroy_tasks,
        "cancel_tasks": cancel_tasks
    }

    print(result)

    return jsonify(tasks_count)

# @app.errorhandler(500)
# def unknown(e):
#     return redirect(url_for('home'))


# @app.errorhandler(404)
# def not_found(e):
#     return redirect(url_for('home'))


if __name__ == "__main__":
    try:
        try:
            asyncio.run(main())
            # app.run(host='127.0.0.1', port=80, debug=True)
        except EOFError:
            print(Fore.MAGENTA + "\nGoody bye !")
            time.sleep(1)
            exit()
    except KeyboardInterrupt:
        print(Fore.MAGENTA + "\nGoody bye !")
        time.sleep(1)
        exit()
