import sys
import os
import time
import atexit
import argparse
import tkinter as tk
from tkinter import messagebox
from database import init_db
from config import (
    check_license, 
    load_config, 
    save_config,
    get_demo_expiry, 
    APP_DATA_DIR, 
    CONFIG_FILE,
    set_main_window
)
from datetime import datetime
from tray import TrayApp, add_to_startup, remove_from_startup

# ✅ ИНИЦИАЛИЗАЦИЯ ЛОГГЕРА ОШИБОК
from error_logger import setup_error_logger
setup_error_logger()

# Импортируем win32api для мьютекса
try:
    import win32event
    import win32api
    import winerror
    import pywintypes
    import win32gui
    import win32con
    import win32process
except ImportError:
    print("Устанавливаю необходимые библиотеки...")
    os.system("pip install pywin32")
    import win32event
    import win32api
    import winerror
    import pywintypes
    import win32gui
    import win32con
    import win32process

# Константа для мьютекса
MUTEX_NAME = "Global\\ZakazMK_Single_Instance_Mutex"

def debug_windows():
    """Выводит информацию обо всех окнах для отладки"""
    def enum_windows_callback(hwnd, windows):
        if win32gui.IsWindowVisible(hwnd):
            class_name = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            print(f"Окно: {hwnd}, Класс: {class_name}, Заголовок: {window_text}")
        return True
    
    print("="*50)
    print("Все видимые окна:")
    win32gui.EnumWindows(enum_windows_callback, None)
    print("="*50)

def find_program_window():
    """Ищет окно программы"""
    try:
        def enum_windows_callback(hwnd, windows):
            class_name = win32gui.GetClassName(hwnd)
            window_text = win32gui.GetWindowText(hwnd)
            
            if class_name == "TkTopLevel" or "Заказ МК" in window_text:
                windows.append(hwnd)
            return True
        
        windows = []
        win32gui.EnumWindows(enum_windows_callback, windows)
        
        if windows:
            return windows[0]
        
        return None
    except Exception as e:
        print(f"⚠️ Ошибка при поиске окна: {e}")
        return None

def activate_existing_instance():
    """Активирует существующий экземпляр программы"""
    try:
        # Ищем окно программы
        hwnd = find_program_window()
        
        if hwnd:
            print(f"✅ Найдено окно программы: {hwnd}")
            
            # Получаем информацию об окне
            window_placement = win32gui.GetWindowPlacement(hwnd)
            print(f"   Состояние: {window_placement[1]}")
            
            # Если окно свернуто - разворачиваем
            if window_placement[1] == win32con.SW_SHOWMINIMIZED:
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            
            # Выводим окно на передний план
            win32gui.ShowWindow(hwnd, win32con.SW_SHOW)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            
            # Отправляем сообщение для установки фокуса на поле ввода
            # Находим дочернее окно (поле ввода)
            def find_child_windows(parent_hwnd):
                children = []
                def enum_child_callback(child_hwnd, _):
                    class_name = win32gui.GetClassName(child_hwnd)
                    # Ищем поле ввода (Edit) или окно Tkinter
                    if class_name in ['Edit', 'TkEntry', 'TkText']:
                        children.append(child_hwnd)
                    return True
                
                win32gui.EnumChildWindows(parent_hwnd, enum_child_callback, None)
                return children
            
            child_windows = find_child_windows(hwnd)
            if child_windows:
                # Устанавливаем фокус на первое поле ввода
                win32gui.SetFocus(child_windows[0])
                print(f"✅ Фокус установлен на поле ввода")
            
            # Небольшая задержка для стабильности
            time.sleep(0.2)
            
            print("✅ Окно программы активировано")
            return True
        else:
            print("❌ Окно программы не найдено")
            return False
    except Exception as e:
        print(f"⚠️ Ошибка при активации окна: {e}")
        return False

def check_single_instance():
    """Проверяет, не запущена ли уже программа"""
    try:
        # Пытаемся создать мьютекс
        mutex = win32event.CreateMutex(None, False, MUTEX_NAME)
        last_error = win32api.GetLastError()
        
        # Проверяем, существует ли уже мьютекс
        if last_error == winerror.ERROR_ALREADY_EXISTS:
            print("⚠️ Программа уже запущена! Активируем существующее окно...")
            
            # Закрываем handle мьютекса
            win32api.CloseHandle(mutex)
            
            # Активируем существующее окно
            if activate_existing_instance():
                print("✅ Существующее окно активировано")
                # Даем время на активацию
                time.sleep(0.5)
                return False
            else:
                print("❌ Не удалось активировать существующее окно")
                
                # Показываем информативное сообщение
                messagebox.showinfo(
                    "Заказ МК",
                    "Программа уже запущена!\n\n"
                    "Она работает в фоновом режиме и доступна в системном трее "
                    "(рядом с часами).\n\n"
                    "Нажмите на иконку программы в трее для открытия окна."
                )
                return False
        else:
            print("✅ Программа запущена (единственный экземпляр)")
            
            # Сохраняем handle мьютекса
            global mutex_handle
            mutex_handle = mutex
            
            # Регистрируем функцию для закрытия мьютекса при выходе
            atexit.register(lambda: win32api.CloseHandle(mutex_handle) if 'mutex_handle' in globals() else None)
            
            return True
            
    except Exception as e:
        print(f"⚠️ Ошибка при проверке единственного экземпляра: {e}")
        return True

def resource_path(relative_path):
    """Путь к ресурсам"""
    appdata_path = os.path.join(os.environ.get('LOCALAPPDATA', ''), 'ZakazMK', relative_path)
    if os.path.exists(appdata_path):
        return appdata_path
    
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))
    return os.path.join(base_path, relative_path)

def parse_arguments():
    """Парсит аргументы командной строки"""
    parser = argparse.ArgumentParser(description='Заказ МК')
    parser.add_argument('--minimized', action='store_true', help='Запуск в свернутом режиме')
    parser.add_argument('--hide', action='store_true', help='Запуск скрытым в трей')
    return parser.parse_args()

def main():
    # ПРОВЕРЯЕМ, НЕ ЗАПУЩЕНА ЛИ УЖЕ ПРОГРАММА
    if not check_single_instance():
        # Программа уже запущена, выходим
        print("❌ Выход - программа уже запущена")
        time.sleep(0.5)
        sys.exit(0)
    
    # Парсим аргументы
    args = parse_arguments()
    
    # Загружаем конфиг
    config = load_config()
    
    # Определяем режим запуска
    minimized = args.minimized or args.hide or config.get('start_minimized', False)
    
    print("=" * 50)
    print("ЗАПУСК ПРОГРАММЫ ЗАКАЗ МК")
    print("=" * 50)
    print(f"📁 Данные сохраняются в: {APP_DATA_DIR}")
    print(f"📁 Конфиг: {CONFIG_FILE}")
    print(f"📌 Режим запуска: {'Скрытый (в трей)' if minimized else 'Обычный'}")
    
    time.sleep(0.3)
    
    # Инициализация базы данных
    init_db()
    
    # Проверка лицензии
    license_ok, error_msg = check_license()
    
    if not license_ok:
        messagebox.showerror("Лицензия", error_msg)
        return
    
    # Splash screen
    splash = None
    if not minimized:
        splash = tk.Tk()
        splash.title("Заказ МК")
        
        screen_width = splash.winfo_screenwidth()
        screen_height = splash.winfo_screenheight()
        
        image_path = resource_path("image.png")
        
        if os.path.exists(image_path):
            try:
                from PIL import Image, ImageTk
                img = Image.open(image_path)
                img = img.resize((400, 300), Image.Resampling.LANCZOS)
                photo = ImageTk.PhotoImage(img)
                
                label = tk.Label(splash, image=photo)
                label.image = photo
                label.pack()
                
                img_width = 400
                img_height = 300
            except Exception as e:
                print(f"Ошибка загрузки изображения: {e}")
                label = tk.Label(splash, text="Заказ МК\n\nЗагрузка...", 
                               font=('Arial', 24, 'bold'), fg='blue', padx=50, pady=50)
                label.pack()
                img_width = 300
                img_height = 200
        else:
            label = tk.Label(splash, text="Заказ МК\n\nЗагрузка...", 
                           font=('Arial', 24, 'bold'), fg='blue', padx=50, pady=50)
            label.pack()
            img_width = 300
            img_height = 200
        
        splash.overrideredirect(True)
        
        x = (screen_width // 2) - (img_width // 2)
        y = (screen_height // 2) - (img_height // 2)
        splash.geometry(f"{img_width}x{img_height}+{x}+{y}")
        
        splash.lift()
        splash.focus_force()
        splash.attributes('-topmost', True)
        
        splash.update()
    
    # Главное окно
    root = tk.Tk()
    root.withdraw()
    
    # Регистрируем главное окно
    set_main_window(root)
    
    # Добавляем в автозагрузку
    if not config.get('startup_added'):
        if add_to_startup():
            config['startup_added'] = True
            save_config(config)
            print("✅ Добавлено в автозагрузку")
    
    icon_path = resource_path("icon.ico")
    if os.path.exists(icon_path):
        try:
            root.iconbitmap(icon_path)
        except Exception as e:
            print(f"Ошибка загрузки иконки: {e}")
    
    if config.get('license_activated'):
        root.title("Заказ МК")
    else:
        expiry = get_demo_expiry()
        if expiry:
            expiry_str = expiry.strftime('%d.%m.%Y %H:%M')
            root.title(f"Заказ МК Демо-версия (до {expiry_str})")
        else:
            root.title("Заказ МК Демо-версия")
    
    from ui import OrderApp
    app = OrderApp(root, config)
    
    # Создаем менеджер трея
    tray = TrayApp(app)
    tray.setup_tray(icon_path)
    
    # Показываем окно если нужно
    if not minimized:
        root.deiconify()
        print("✅ Окно программы показано")
    else:
        print("✅ Программа запущена в фоновом режиме")
    
    # Убираем сплеш
    if splash:
        splash.destroy()
    
    # Обработчик закрытия
    root.protocol("WM_DELETE_WINDOW", tray.on_closing)
    
    root.mainloop()
    # Обработчик закрытия
    root.protocol("WM_DELETE_WINDOW", tray.on_closing)
    
    # ✅ ДОБАВЬТЕ ОБРАБОТЧИК ВЫХОДА
    def on_exit():
        """Очистка при выходе"""
        if hasattr(tray, 'tray_icon') and tray.tray_icon:
            try:
                tray.tray_icon.stop()
            except:
                pass
        print("✅ Программа завершена")
    
    atexit.register(on_exit)
    
    try:
        root.mainloop()
    finally:
        # ✅ ГАРАНТИРОВАННАЯ ОЧИСТКА
        on_exit()
if __name__ == "__main__":
    main()