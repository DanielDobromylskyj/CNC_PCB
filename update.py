import urllib.request
import zipfile
import io
import os
import subprocess
import time
import shutil


url = f"https://github.com/DanielDobromylskyj/CNC_PCB/archive/refs/heads/main.zip"

response = urllib.request.urlopen(url)
zip_data = response.read()


with zipfile.ZipFile(io.BytesIO(zip_data), "r") as zip_ref:
    zip_ref.extractall()

repo_folder = "CNC_PCB-main"
if os.path.exists(repo_folder):
    for item in os.listdir(repo_folder):
        src_path = os.path.join(repo_folder, item)
        dst_path = os.path.join(".", item)

        if os.path.exists(dst_path):  # Remove existing files/folders
            if os.path.isdir(dst_path):
                shutil.rmtree(dst_path)  # Remove old folder
            else:
                os.remove(dst_path)  # Remove old file

        shutil.move(src_path, dst_path)  # Move new file/folder

    shutil.rmtree(repo_folder)  # Clean up extracted folder

print(f"Repository downloaded and extracted successfully, Trying setup...")

if os.name == "nt":
    subprocess.run(["setup.bat"], shell=True)
else:
    print("Didn't attempt to run setup, windows only (.bat)")