# updater.py
import os
import sys
import json
import requests
import hashlib
import subprocess
import tempfile
from datetime import datetime

# ✅ URL ФАЙЛА С ВЕРСИЕЙ (разместить на вашем сайте)
VERSION_URL = "https://ваш-сайт.ru/updates/version.json"
# ✅ URL СКАЧИВАНИЯ НОВОЙ ВЕРСИИ (указать в version.json)

def get_current_version():
    """Получает текущую версию программы"""
    return "1.7"  # ✅ Обновлять при каждом релизе!

def check_for_update():
    """Проверяет наличие обновлений"""
    try:
        # Загружаем информацию о версии
        response = requests.get(VERSION_URL, timeout=10)
        if response.status_code != 200:
            print(f"⚠️ Не удалось проверить обновления: {response.status_code}")
            return None
        
        remote_version = response.json()
        current_version = get_current_version()
        
        # Сравниваем версии
        if is_newer_version(remote_version['version'], current_version):
            print(f"✅ Доступно обновление: {current_version} → {remote_version['version']}")
            return remote_version
        else:
            print(f"✅ Установлена актуальная версия: {current_version}")
            return None
            
    except Exception as e:
        print(f"❌ Ошибка проверки обновлений: {e}")
        return None

def is_newer_version(remote, current):
    """Сравнивает версии (возвращает True если remote новее)"""
    try:
        remote_parts = [int(x) for x in remote.split('.')]
        current_parts = [int(x) for x in current.split('.')]
        
        for i in range(max(len(remote_parts), len(current_parts))):
            r = remote_parts[i] if i < len(remote_parts) else 0
            c = current_parts[i] if i < len(current_parts) else 0
            if r > c:
                return True
            elif r < c:
                return False
        return False
    except:
        return False

def download_update(download_url, progress_callback=None):
    """Скачивает файл обновления"""
    try:
        temp_dir = tempfile.gettempdir()
        temp_file = os.path.join(temp_dir, 'ZakazMK_Update.exe')
        
        response = requests.get(download_url, stream=True, timeout=30)
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        
        with open(temp_file, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    if progress_callback and total_size > 0:
                        progress_callback(downloaded / total_size)
        
        print(f"✅ Файл загружен: {temp_file}")
        return temp_file
        
    except Exception as e:
        print(f"❌ Ошибка загрузки: {e}")
        return None

def install_update(exe_path):
    """Устанавливает обновление (перезапускает программу с новым exe)"""
    try:
        # Создаём batch-файл для установки
        temp_dir = tempfile.gettempdir()
        batch_file = os.path.join(temp_dir, 'install_update.bat')
        
        current_exe = sys.executable if getattr(sys, 'frozen', False) else sys.argv[0]
        
        with open(batch_file, 'w', encoding='utf-8') as f:
            f.write(f'@echo off\n')
            f.write(f'timeout /t 2 /nobreak > nul\n')
            f.write(f'copy /Y "{exe_path}" "{current_exe}"\n')
            f.write(f'start "" "{current_exe}"\n')
            f.write(f'del "{batch_file}"\n')
        
        # Запускаем batch-файл
        subprocess.Popen(batch_file, creationflags=subprocess.DETACHED_PROCESS)
        
        # Закрываем текущую программу
        os._exit(0)
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка установки: {e}")
        return False