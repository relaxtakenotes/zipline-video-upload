import httpx
import pyperclip

import json
import mimetypes
import os
import random
import string
import subprocess
import shlex
import traceback
import time

TOKEN = ""
CHUNK_SIZE = 20_000_000
DOMAIN = "https://cool.com"

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
        
def main():
    file_path = pyperclip.paste()
    if len(file_path) >= 0 and file_path[0] == "\"" and file_path[-1] == "\"":
        file_path = file_path[1:-1]
    
    print(f"[{file_path}]")
    print("Do we continue? [Y/N]")
    if not input().lower().startswith("y"):
        exit()

    pipe = subprocess.PIPE

    print("Opening LosslessCut...")

    ignore = {}

    dirname = os.path.dirname(file_path)
    files = os.listdir(dirname)

    for file in files:
        input_file_base, input_file_ext = os.path.splitext(os.path.basename(file_path))
        current_file_base, current_file_ext = os.path.splitext(os.path.basename(file))
        if input_file_ext == current_file_ext and input_file_base in current_file_base and input_file_base != current_file_base:
            ignore[file] = True
            
    subprocess.Popen(shlex.split(f"LosslessCut \"{file_path}\""), stdout=pipe).communicate()
    time.sleep(1)
    
    done = False
    cut_path = ""
    while not done:
        files = os.listdir(dirname)

        for file in files:
            input_file_base, input_file_ext = os.path.splitext(os.path.basename(file_path))
            current_file_base, current_file_ext = os.path.splitext(os.path.basename(file))
            if input_file_ext == current_file_ext and input_file_base in current_file_base and input_file_base != current_file_base and not ignore.get(file):
                done = True
                cut_path = os.path.join(dirname, file)
                break
        
        time.sleep(1)

    i_base, _ = os.path.splitext(cut_path)
    intermediate_path = i_base + "_merged.mp4"

    print(f"Merging audio tracks... [{cut_path} --> {intermediate_path}]")
    num_of_inputs, _ = subprocess.Popen(shlex.split(f"ffprobe -loglevel error -select_streams a -show_entries stream=index -of csv=p=0 \"{cut_path}\""), stdout=pipe).communicate()
    num_of_inputs = num_of_inputs.count(b"\n")
    subprocess.Popen(shlex.split(f"ffmpeg -i \"{cut_path}\" -c:v copy -c:a aac -b:a 160k -ac 2 -filter_complex \"amerge=inputs={num_of_inputs}\" \"{intermediate_path}\""), stdout=pipe).communicate()
    
    base, _ = os.path.splitext(intermediate_path)
    end_path = base + "_braked.mp4"

    print(f"Converting... [{intermediate_path} --> {end_path}]")
    subprocess.Popen(shlex.split(f"HandBrakeCLI --preset-import-file \"{os.path.abspath("preset.json")}\" -Z \"Source 1080P\" -i \"{intermediate_path}\" -o \"{end_path}\""), stdout=pipe).communicate()

    print(f"Uploading... [{end_path}]")
    upload(end_path)

    os.remove(end_path)
    os.remove(intermediate_path)
    os.remove(cut_path)

try:
    main()
except Exception:
    print(traceback.format_exc())

input()