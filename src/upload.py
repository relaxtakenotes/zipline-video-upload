import httpx
import pyperclip

from tkinter import Tk
from tkinter.filedialog import askopenfilename

Tk().withdraw()

import json
import mimetypes
import os
import random
import string
import subprocess
import shlex
import traceback
import time
import ctypes

TOKEN = ""
CHUNK_SIZE = 20_000_000
DOMAIN = "https://cool.com"

def execute(cmd):
    return subprocess.Popen(shlex.split(cmd), stdout=subprocess.PIPE).communicate()

def upload(file_path):
    chunks = []
    chunks_length = 0
    file_size = 0

    with open(file_path, "rb") as file:
        while content := file.read(CHUNK_SIZE):
            chunks.append(content)
            file_size += len(content)
            chunks_length += 1

    file_name = os.path.basename(file_path)
    file_type = mimetypes.guess_type(file_path)[0]
    identifier = ''.join(random.choice(string.ascii_lowercase) for i in range(6))

    last_chunk_pos = 0
    for i, chunk in enumerate(chunks):
        chunk_length = len(chunk)

        print(f"Uploading chunk {i + 1}/{chunks_length}")

        response = httpx.post(DOMAIN + "/api/upload", 
            timeout = 9999,
            files = {"file": ("blob", chunk)}, 
            headers = {
                "Authorization": TOKEN,
                "Accept-Encoding": "gzip, deflate, br, zstd",
                "Content-Range": f"bytes {last_chunk_pos}-{last_chunk_pos + chunk_length}/{file_size}",
                "X-Zipline-Partial-FileName": file_name,
                "X-Zipline-Partial-MimeType": file_type,
                "X-Zipline-Partial-Identifier": identifier,
                "X-Zipline-Partial-LastChunk": "true" if i >= chunks_length - 1 else "false",
                "Embed": "true"
            }
        )

        if response and response.status_code == 200 and len(response.text) > 0:
            decoded = json.loads(response.text)

            if decoded.get("success"):
                print(f"Uploaded chunk {i + 1}/{chunks_length}")
            
            if decoded.get("files"):
                print(decoded.get("files")[0])
        else:
            raise Exception(f"Failed to upload chunk {i}")
        
        last_chunk_pos += chunk_length

def lossless_cut_process(file_path):
    ignore = {}

    dirname = os.path.dirname(file_path)
    files = os.listdir(dirname)

    for file in files:
        input_file_base, input_file_ext = os.path.splitext(os.path.basename(file_path))
        current_file_base, current_file_ext = os.path.splitext(os.path.basename(file))
        if input_file_ext == current_file_ext and input_file_base in current_file_base and input_file_base != current_file_base:
            ignore[file] = True
            
    execute(f"LosslessCut \"{file_path}\"")
    time.sleep(1)
    
    done = False
    output_path = ""
    while not done:
        files = os.listdir(dirname)

        for file in files:
            input_file_base, input_file_ext = os.path.splitext(os.path.basename(file_path))
            current_file_base, current_file_ext = os.path.splitext(os.path.basename(file))
            if input_file_ext == current_file_ext and input_file_base in current_file_base and input_file_base != current_file_base and not ignore.get(file):
                done = True
                output_path = os.path.join(dirname, file)
                break
        
        time.sleep(1)
    
    return output_path

def merge_tracks(file_path):
    base, _ = os.path.splitext(file_path)
    output_path = base + "_merged.mp4"
    
    num_of_inputs, _ = execute(f"ffprobe -loglevel error -select_streams a -show_entries stream=index -of csv=p=0 \"{file_path}\"")
    num_of_inputs = num_of_inputs.count(b"\n")
    execute(f"ffmpeg -i \"{file_path}\" -c:v copy -c:a aac -b:a 160k -ac 2 -filter_complex \"amerge=inputs={num_of_inputs}\" \"{output_path}\"")

    return output_path

def compress(file_path):
    base, _ = os.path.splitext(file_path)
    output_path = base + "_braked.mp4"
    
    execute(f"HandBrakeCLI --preset-import-file \"{os.path.abspath("preset.json")}\" -Z \"Source 1080P\" -i \"{file_path}\" -o \"{output_path}\"")
    
    return output_path

def main():
    window = ctypes.windll.kernel32.GetConsoleWindow()

    file_path = pyperclip.paste()
    if len(file_path) >= 0 and file_path[0] == "\"" and file_path[-1] == "\"":
        file_path = file_path[1:-1]
    
    if not os.path.exists(file_path):
        file_path = askopenfilename()
    
    if len(file_path) <= 0:
        exit()
    
    ctypes.windll.user32.SetForegroundWindow(window)

    choice = input(f"[{file_path}]\nDo we continue? [Y/N/(R)eset]: ").lower()
    if choice.startswith("n"):
        exit()
    elif choice.startswith("r"):
        main()
        return

    print("Opening LosslessCut...")
    cut_path = lossless_cut_process(file_path)

    print(f"Merging audio tracks...")
    merge_path = merge_tracks(cut_path)
    
    print(f"Converting...")
    end_path = compress(merge_path)

    if TOKEN != "none":
        print(f"Uploading... [{end_path}]")
        upload(end_path)
    
    ctypes.windll.user32.FlashWindow(window, True)

    os.remove(cut_path)
    os.remove(merge_path)

    if TOKEN != "none" and input("Do you wish to keep the end file? [Y/N]: ").lower().startswith("n"):
        os.remove(end_path)
    else:
        execute(f"explorer /select {end_path}")
    
    exit()

if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(traceback.format_exc())
    input()