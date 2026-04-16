import os
import json
import winreg
from datetime import datetime, timedelta

# ===== ПУТИ И КОНСТАНТЫ =====
APP_DATA_DIR = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ZakazMK')
os.makedirs(APP_DATA_DIR, exist_ok=True)

CONFIG_FILE = os.path.join(APP_DATA_DIR, "config.json")
DB_FILE = os.path.join(APP_DATA_DIR, "database.db")
ORDERS_DB_FILE = os.path.join(APP_DATA_DIR, "orders.db")
INVENTORY_DB_FILE = os.path.join(APP_DATA_DIR, "inventory.db")
PDF_OUTPUT_DIR = os.path.join(APP_DATA_DIR, 'Заказы')
os.makedirs(PDF_OUTPUT_DIR, exist_ok=True)

# ===== РЕЕСТР =====
REG_PATH = r"Software\ZakazMK"
LICENSE_CODE = "MK-2024-PRO-LICENSE"

main_window = None

def set_main_window(window):
    global main_window
    main_window = window

def is_main_window_alive():
    global main_window
    try:
        return main_window and main_window.winfo_exists()
    except:
        return False

def _read_from_registry(name, default=None):
    """Чтение значения из реестра"""
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        value, _ = winreg.QueryValueEx(key, name)
        winreg.CloseKey(key)
        return value
    except FileNotFoundError:
        return default
    except Exception:
        return default

def _write_to_registry(name, value):
    """Запись значения в реестр"""
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        if isinstance(value, bool):
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, 1 if value else 0)
        elif isinstance(value, int):
            winreg.SetValueEx(key, name, 0, winreg.REG_DWORD, value)
        elif isinstance(value, str):
            winreg.SetValueEx(key, name, 0, winreg.REG_SZ, value)
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"⚠️ Ошибка записи в реестр: {e}")
        return False

def get_default_config():
    return {
        'license_activated': False,
        'first_run': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'window_width': 1200,
        'window_height': 700,
        'window_x': 100,
        'window_y': 100,
        'sash_position': 400,
        'startup_added': False,
        'start_minimized': False,
        'close_to_tray': True,
        'ask_save_on_close': True,
        'inventory_sort_column': 'Наименование',
        'inventory_sort_reverse': False,
        'cutting_stock_length': 6000,
        'show_cutting_maps': False,
        'kerf_width': 3,
        'auto_backup_on_close': True,
        'auto_backup_enabled': True
    }

def load_config():
    """Загружает конфиг из файла + лицензию ИЗ РЕЕСТРА"""
    # Загружаем файл
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            # Добавляем недостающие поля
            default = get_default_config()
            for key in default:
                if key not in config:
                    config[key] = default[key]
            
            # ✅ ГЛАВНОЕ: Читаем лицензию из реестра, а не из файла!
            license_activated = _read_from_registry('license_activated', 0)
            config['license_activated'] = bool(license_activated)
            
            # ✅ Читаем first_run из реестра (приоритет над файлом!)
            first_run_reg = _read_from_registry('first_run')
            if first_run_reg:
                config['first_run'] = first_run_reg
            
            return config
        except Exception as e:
            print(f"⚠️ Ошибка загрузки конфига: {e}")
    
    # Если файла нет — создаём новый
    new_config = get_default_config()
    save_config(new_config)
    return new_config

def save_config(config):
    """Сохраняет настройки окна в файл (лицензия — только в реестр!)"""
    try:
        # Убираем лицензию из файла — она теперь в реестре
        config_copy = {k: v for k, v in config.items() 
                      if k not in ['license_activated', 'license_key', 'activated_at']}
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config_copy, f, ensure_ascii=False, indent=2)
        return True
    except Exception as e:
        print(f"⚠️ Ошибка сохранения конфига: {e}")
        return False

def check_license():
    """Проверка лицензии"""
    # Проверяем реестр
    license_activated = _read_from_registry('license_activated', 0)
    if license_activated == 1:
        return True, None
    
    # Если в реестре нет — проверяем файл (для обратной совместимости)
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            if config.get('license_activated'):
                return True, None
        except:
            pass
    
    # Демо-режим
    first_run = _read_from_registry('first_run')
    if not first_run and os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            first_run = config.get('first_run')
        except:
            pass
    
    if first_run:
        try:
            first_date = datetime.strptime(first_run, '%Y-%m-%d %H:%M:%S')
            expiry_date = first_date + timedelta(days=2)
            if datetime.now() > expiry_date:
                return False, f"Срок действия демо-версии истёк!\n\nИстёк: {expiry_date.strftime('%d.%m.%Y %H:%M')}\nПожалуйста, активируйте лицензию."
        except:
            pass
    
    return True, None

def activate_license(code):
    """Активация по ключу"""
    if code.strip() == LICENSE_CODE:
        _write_to_registry('license_activated', 1)
        _write_to_registry('license_key', code.strip())
        _write_to_registry('activated_at', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        # Обновляем файл для совместимости
        config = load_config()
        config['license_activated'] = True
        save_config(config)
        return True
    return False

def reset_license():
    """Сброс лицензии + ПЕРЕЗАПУСК ДЕМО-ПЕРИОДА"""
    # ✅ Удаляем лицензию из реестра
    try:
        key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, REG_PATH)
        winreg.DeleteValue(key, 'license_activated')
        winreg.CloseKey(key)
    except:
        pass
    
    # ✅ ОБНОВЛЯЕМ first_run на текущую дату (в реестр!)
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    _write_to_registry('first_run', now)
    
    # ✅ Обновляем файл конфига
    config = load_config()
    config['license_activated'] = False
    config['first_run'] = now  # ← ЭТО ВАЖНО!
    config.pop('license_key', None)
    config.pop('activated_at', None)
    save_config(config)
    
    print(f"✅ Лицензия сброшена, демо-период обновлён до {now}")
    return True

def get_demo_expiry():
    """Возвращает дату окончания демо"""
    # ✅ Читаем first_run из реестра (приоритет!)
    first_run = _read_from_registry('first_run')
    if not first_run and os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                config = json.load(f)
            first_run = config.get('first_run')
        except:
            pass
    
    if first_run:
        try:
            first_date = datetime.strptime(first_run, '%Y-%m-%d %H:%M:%S')
            return first_date + timedelta(days=2)
        except:
            pass
    return None
