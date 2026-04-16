import os
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox
import pystray
from PIL import Image, ImageDraw
import subprocess
import atexit

# ========== ФУНКЦИИ ДЛЯ АВТОЗАГРУЗКИ ==========
def add_to_startup():
    """Добавляет программу в автозагрузку"""
    import winreg
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "ZakazMK"
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        
        if getattr(sys, 'frozen', False):
            app_path = sys.executable
        else:
            app_path = os.path.abspath(sys.argv[0])
        
        winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{app_path}" --minimized')
        winreg.CloseKey(key)
        print(f"✅ Программа добавлена в автозагрузку: {app_path} --minimized")
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления в автозагрузку: {e}")
        return False


def remove_from_startup():
    """Удаляет программу из автозагрузки"""
    import winreg
    
    key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
    app_name = "ZakazMK"
    
    try:
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        winreg.DeleteValue(key, app_name)
        winreg.CloseKey(key)
        print("✅ Программа удалена из автозагрузки")
        return True
    except Exception as e:
        print(f"❌ Ошибка удаления из автозагрузки: {e}")
        return False


# ========== КЛАСС TrayApp ==========
class TrayApp:
    def __init__(self, main_app):
        self.main_app = main_app
        self.root = main_app.root
        self.tray_icon = None
        self.is_hidden = True
        self.icon_image = None
        self.tray_thread = None
        self._is_quitting = False
        
    def create_image(self, icon_path=None):
        """Создает иконку для трея из файла .ico"""
        if icon_path and os.path.exists(icon_path):
            try:
                img = Image.open(icon_path)
                if img.mode != 'RGBA':
                    img = img.convert('RGBA')
                img = img.resize((64, 64), Image.Resampling.LANCZOS)
                self.icon_image = img
                return img
            except Exception as e:
                print(f"❌ Ошибка загрузки иконки для трея: {e}")
        
        print("⚠️ Создаем иконку по умолчанию")
        image = Image.new('RGBA', (64, 64), color='blue')
        draw = ImageDraw.Draw(image)
        draw.rectangle((16, 16, 48, 48), fill='white')
        draw.text((20, 22), "MK", fill='black')
        return image
    
    def show_window(self, icon=None, item=None):
        """Показывает главное окно"""
        print("🔍 Пытаемся показать окно")
        
        def _show():
            try:
                if not self.root.winfo_exists():
                    print("❌ Окно уже уничтожено")
                    return
                
                self.root.deiconify()
                self.root.lift()
                self.root.focus_force()
                self.root.state('normal')
                
                self.root.update_idletasks()
                self.root.update()
                
                if hasattr(self.main_app, 'force_focus'):
                    self.root.after(100, self.main_app.force_focus)
                
                if hasattr(self.main_app, 'delayed_restore_sash'):
                    self.root.after(200, self.main_app.delayed_restore_sash)
                
                self.is_hidden = False
                print("✅ Окно показано")
            except Exception as e:
                print(f"❌ Ошибка при показе окна: {e}")
        
        self.root.after(0, _show)
    
    def hide_window(self, icon=None, item=None):
        """Прячет окно в трей"""
        print("🔍 Прячем окно в трей")
        
        def _hide():
            try:
                if not self.root.winfo_exists():
                    return
                self.root.withdraw()
                self.is_hidden = True
                print("✅ Окно скрыто")
            except Exception as e:
                print(f"❌ Ошибка при скрытии окна: {e}")
        
        self.root.after(0, _hide)
    
    def quit_app(self, icon=None, item=None):
        """Полностью закрывает приложение"""
        print("🔍 Завершаем работу приложения")
        
        if self._is_quitting:
            return
        self._is_quitting = True
        
        def _quit():
            # ✅ ОСТАНАВЛИВАЕМ ИКОНКУ ТРЕЯ
            if self.tray_icon:
                try:
                    print("🛑 Останавливаем иконку трея...")
                    self.tray_icon.stop()
                    print("✅ Иконка трея остановлена")
                except Exception as e:
                    print(f"⚠️ Ошибка при остановке иконки: {e}")
            
            # Небольшая задержка
            time.sleep(0.1)
            
            # Закрываем главное окно
            try:
                if self.root.winfo_exists():
                    self.root.quit()
                    self.root.destroy()
            except:
                pass
            
            # Принудительный выход
            os._exit(0)
        
        # Выполняем в основном потоке
        if self.root and self.root.winfo_exists():
            self.root.after(0, _quit)
        else:
            _quit()
    
    def on_left_click(self):
        """Обработчик левого клика (имитация через default_action)"""
        print("🖱️ Левый клик по иконке")
        self.show_window()
    
    def setup_tray(self, icon_path=None):
        """Настраивает иконку в трее"""
        
        # Создаем иконку
        image = self.create_image(icon_path)
        
        # ✅ СОЗДАЕМ МЕНЮ С DEFAULT_ACTION
        menu = pystray.Menu(
            pystray.MenuItem("Показать", self.show_window, default=True),
            pystray.MenuItem("Скрыть", self.hide_window),
            pystray.MenuItem("Выход", self.quit_app),
        )
        
        # Создаем иконку с меню
        self.tray_icon = pystray.Icon(
            "ZakazMK", 
            image, 
            "Заказ МК", 
            menu
        )
        
        # Запускаем иконку в отдельном потоке (НЕ daemon!)
        def run_tray():
            try:
                self.tray_icon.run()
            except Exception as e:
                if not self._is_quitting:
                    print(f"❌ Ошибка в потоке трея: {e}")
            finally:
                print("✅ Поток трея завершен")
        
        self.tray_thread = threading.Thread(target=run_tray, daemon=False)
        self.tray_thread.start()
        
        # ✅ РЕГИСТРИРУЕМ ОЧИСТКУ ПРИ ВЫХОДЕ
        atexit.register(self._cleanup_tray)
        
        print("✅ Иконка в трее запущена")
        print("   - Левый клик: показать окно (действие по умолчанию)")
        print("   - Правый клик: меню")
    
    def _cleanup_tray(self):
        """Очистка при выходе"""
        if self.tray_icon:
            try:
                self.tray_icon.stop()
            except:
                pass
    
    def on_closing(self):
        """Обработчик закрытия окна - проверяет настройки"""
        print("🔍 Закрытие окна - проверяем настройки")
        
        # ✅ ПРОВЕРЯЕМ НАСТРОЙКУ close_to_tray
        close_to_tray = self.main_app.config.get('close_to_tray', True)
        
        if close_to_tray:
            # Если настройка "закрывать в трей" - прячем окно
            print("📌 Настройка close_to_tray = True - прячем в трей")
            try:
                if hasattr(self.main_app, 'main_paned'):
                    sash_pos = self.main_app.main_paned.sashpos(0)
                    if sash_pos > 0:
                        self.main_app.config['sash_position'] = sash_pos
                        from config import save_config
                        save_config(self.main_app.config)
                        print(f"📏 Сохранена позиция разделителя: {sash_pos}")
            except Exception as e:
                print(f"⚠️ Ошибка при сохранении позиции разделителя: {e}")
            
            self.hide_window()
            return True
        else:
            # ✅ Если настройка "закрывать полностью" - закрываем программу
            print("📌 Настройка close_to_tray = False - закрываем программу")
            self.quit_app()
            return True