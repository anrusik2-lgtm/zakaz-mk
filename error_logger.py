import os
import sys
import traceback
from datetime import datetime
from config import APP_DATA_DIR

# Путь к файлу логов
LOG_FILE = os.path.join(APP_DATA_DIR, 'errors.log')

def setup_error_logger():
    """Настраивает перехват всех ошибок в программе"""
    
    def log_error(error_type, value, tb):
        """Записывает ошибку в лог-файл"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Формируем сообщение об ошибке
        error_msg = f"\n{'='*80}\n"
        error_msg += f"⏰ Время: {timestamp}\n"
        error_msg += f"📝 Тип: {error_type.__name__}\n"
        error_msg += f"💬 Сообщение: {value}\n"
        error_msg += f"{'='*80}\n"
        error_msg += f"📋 Трассировка:\n{traceback.format_tb(tb)}\n"
        
        # Записываем в файл
        try:
            with open(LOG_FILE, 'a', encoding='utf-8') as f:
                f.write(error_msg)
            print(f"❌ Ошибка записана в лог: {LOG_FILE}")
        except Exception as e:
            print(f"⚠️ Не удалось записать ошибку в лог: {e}")
        
        # Показываем в консоли
        print(error_msg)
    
    # ✅ ПЕРЕХВАТЫВАЕМ ВСЕ НЕОБРАБОТАННЫЕ ОШИБКИ
    sys.excepthook = log_error
    
    # ✅ ПЕРЕХВАТЫВАЕМ ОШИБКИ В TKINTER
    import tkinter as tk
    original_report_callback = tk.Tk.report_callback_exception
    
    def report_callback_exception(self, exc, val, tb):
        log_error(exc, val, tb)
        original_report_callback(self, exc, val, tb)
    
    tk.Tk.report_callback_exception = report_callback_exception
    
    print(f"✅ Логгер ошибок настроен. Файл: {LOG_FILE}")
    return LOG_FILE

def get_error_logs(start_date=None, end_date=None, search_text=None):
    """
    Читает логи ошибок из файла
    
    Args:
        start_date: дата начала (datetime)
        end_date: дата конца (datetime)
        search_text: текст для поиска в ошибках
    
    Returns:
        список словарей с ошибками
    """
    if not os.path.exists(LOG_FILE):
        return []
    
    errors = []
    current_error = None
    
    try:
        with open(LOG_FILE, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                
                # Начало новой ошибки
                if line.startswith('⏰ Время:'):
                    if current_error:
                        errors.append(current_error)
                    
                    timestamp_str = line.replace('⏰ Время:', '').strip()
                    try:
                        timestamp = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S')
                        
                        # Фильтр по датам
                        if start_date and timestamp < start_date:
                            current_error = None
                            continue
                        if end_date and timestamp > end_date:
                            current_error = None
                            continue
                        
                        current_error = {
                            'timestamp': timestamp,
                            'timestamp_str': timestamp_str,
                            'type': '',
                            'message': '',
                            'traceback': ''
                        }
                    except:
                        current_error = None
                
                # Тип ошибки
                elif line.startswith('📝 Тип:') and current_error:
                    current_error['type'] = line.replace('📝 Тип:', '').strip()
                
                # Сообщение
                elif line.startswith('💬 Сообщение:') and current_error:
                    current_error['message'] = line.replace('💬 Сообщение:', '').strip()
                
                # Трассировка
                elif line.startswith('📋 Трассировка:') and current_error:
                    current_error['traceback'] = line.replace('📋 Трассировка:', '').strip()
                
                # Продолжение трассировки
                elif current_error and current_error.get('traceback'):
                    current_error['traceback'] += line + '\n'
            
            # Добавляем последнюю ошибку
            if current_error:
                errors.append(current_error)
    
    except Exception as e:
        print(f"⚠️ Ошибка чтения логов: {e}")
        return []
    
    # ✅ ФИЛЬТР ПО ТЕКСТУ
    if search_text:
        search_lower = search_text.lower()
        errors = [e for e in errors if 
                 search_lower in e.get('message', '').lower() or
                 search_lower in e.get('type', '').lower() or
                 search_lower in e.get('traceback', '').lower()]
    
    # Сортируем по дате (новые сверху)
    errors.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return errors

def clear_error_logs():
    """Очищает файл логов"""
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'w', encoding='utf-8') as f:
                f.write('')
            return True
        except:
            return False
    return True

def get_log_file_path():
    """Возвращает путь к файлу логов"""
    return LOG_FILE