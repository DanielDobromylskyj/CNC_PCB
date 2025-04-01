@echo off
py -m pip --version >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Pip not found, installing...
    py -m ensurepip
    py -m pip install --upgrade pip
) ELSE (
    echo Pip is already installed.
    py -m pip install --upgrade pip
    echo Pip updated.

)

py -m pip --version

py -m pip install matplotlib numpy pillow

py -c "import shutil, site, os; src=os.path.join(site.getsitepackages()[0], 'lib', 'site-packages', 'matplotlib'); dest=os.getcwd(); shutil.copytree(src, os.path.join(dest, 'matplotlib'), dirs_exist_ok=True) if os.path.exists(src) else print(f'Folder not found: ', src)"

REM py -c "import shutil, site, os; src=os.path.join(site.getsitepackages()[0], 'lib', 'site-packages', 'numpy'); dest=os.getcwd(); shutil.copytree(src, os.path.join(dest, 'numpy'), dirs_exist_ok=True) if os.path.exists(src) else print(f'Folder not found: ', src)"


echo copied site packages to working directory

echo py main.py > start.bat
echo pause. >> start.bat

echo Created start.bat
echo Complete!