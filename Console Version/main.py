import os
import asyncio
from tqdm import tqdm
from fuzzywuzzy import fuzz
import time
import platform
from plyer import notification
import psutil
from colorama import Fore, Style
import random


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



if __name__ == "__main__":
    try:
        try:
            asyncio.run(main())
        except EOFError:
            print(Fore.MAGENTA + "\nGoody bye !")
            time.sleep(1)
            exit()
    except KeyboardInterrupt:
        print(Fore.MAGENTA + "\nGoody bye !")
        time.sleep(1)
        exit()
