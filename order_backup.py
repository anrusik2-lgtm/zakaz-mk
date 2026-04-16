import os
import json
from datetime import datetime
from config import APP_DATA_DIR

# Папка для бэкапов заказов
BACKUP_DIR = os.path.join(APP_DATA_DIR, 'order_backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

def create_order_backup(order_number, order_items, order_year=None):
    """✅ Создаёт бэкап заказа перед сохранением"""
    if not order_number or not order_items:
        return None
    
    if order_year is None:
        order_year = datetime.now().year
    
    # Создаём папку для бэкапов этого заказа
    order_backup_dir = os.path.join(BACKUP_DIR, f"{order_number}_{order_year}")
    os.makedirs(order_backup_dir, exist_ok=True)
    
    # Имя файла с временной меткой
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_file = os.path.join(order_backup_dir, f"backup_{timestamp}.json")
    
    # Данные для бэкапа
    backup_data = {
        'order_number': order_number,
        'order_year': order_year,
        'timestamp': timestamp,
        'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'items': order_items,
        'items_count': len(order_items)
    }
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(backup_data, f, ensure_ascii=False, indent=2)
        
        print(f"💾 Бэкап создан: {backup_file}")
        print(f"   Позиций в заказе: {len(order_items)}")
        
        # ✅ Очищаем старые бэкапы (оставляем последние 50)
        cleanup_old_backups(order_backup_dir, max_backups=50)
        
        return backup_file
    except Exception as e:
        print(f"❌ Ошибка создания бэкапа: {e}")
        return None

def get_order_backups(order_number, order_year=None):
    """✅ Получает список бэкапов для заказа"""
    if order_year is None:
        order_year = datetime.now().year
    
    order_backup_dir = os.path.join(BACKUP_DIR, f"{order_number}_{order_year}")
    
    if not os.path.exists(order_backup_dir):
        return []
    
    backups = []
    for filename in os.listdir(order_backup_dir):
        if filename.startswith('backup_') and filename.endswith('.json'):
            filepath = os.path.join(order_backup_dir, filename)
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    backup_data = json.load(f)
                backups.append({
                    'filepath': filepath,
                    'timestamp': backup_data.get('timestamp', ''),
                    'created_at': backup_data.get('created_at', ''),
                    'items_count': backup_data.get('items_count', 0),
                    'data': backup_data
                })
            except:
                pass
    
    # Сортируем по времени (новые сверху)
    backups.sort(key=lambda x: x['timestamp'], reverse=True)
    
    print(f"📋 Найдено бэкапов для заказа {order_number}: {len(backups)}")
    return backups

def restore_order_from_backup(backup_filepath):
    """✅ Восстанавливает заказ из бэкапа"""
    if not os.path.exists(backup_filepath):
        return None
    
    try:
        with open(backup_filepath, 'r', encoding='utf-8') as f:
            backup_data = json.load(f)
        
        print(f"✅ Заказ восстановлен из бэкапа: {backup_filepath}")
        print(f"   Позиций: {backup_data.get('items_count', 0)}")
        
        return backup_data.get('items', [])
    except Exception as e:
        print(f"❌ Ошибка восстановления из бэкапа: {e}")
        return None

def cleanup_old_backups(order_backup_dir, max_backups=50):
    """✅ Удаляет старые бэкапы, оставляя только последние N"""
    if not os.path.exists(order_backup_dir):
        return
    
    backups = []
    for filename in os.listdir(order_backup_dir):
        if filename.startswith('backup_') and filename.endswith('.json'):
            filepath = os.path.join(order_backup_dir, filename)
            try:
                mtime = os.path.getmtime(filepath)
                backups.append((filepath, mtime))
            except:
                pass
    
    # Сортируем по времени (старые снизу)
    backups.sort(key=lambda x: x[1])
    
    # Удаляем старые, если больше max_backups
    while len(backups) > max_backups:
        old_backup = backups.pop(0)
        try:
            os.remove(old_backup[0])
            print(f"🗑️ Удалён старый бэкап: {old_backup[0]}")
        except:
            pass

def get_all_backup_orders():
    """✅ Получает список всех заказов, для которых есть бэкапы"""
    if not os.path.exists(BACKUP_DIR):
        return []
    
    backup_orders = []
    for folder_name in os.listdir(BACKUP_DIR):
        if '_' in folder_name:
            parts = folder_name.rsplit('_', 1)
            if len(parts) == 2 and parts[1].isdigit():
                order_number = parts[0]
                order_year = int(parts[1])
                
                # Считаем количество бэкапов
                order_backup_dir = os.path.join(BACKUP_DIR, folder_name)
                backup_count = len([f for f in os.listdir(order_backup_dir) 
                                   if f.startswith('backup_') and f.endswith('.json')])
                
                if backup_count > 0:
                    # Берём последний бэкап для даты
                    last_backup = None
                    for filename in os.listdir(order_backup_dir):
                        if filename.startswith('backup_') and filename.endswith('.json'):
                            filepath = os.path.join(order_backup_dir, filename)
                            try:
                                with open(filepath, 'r', encoding='utf-8') as f:
                                    backup_data = json.load(f)
                                if last_backup is None or backup_data.get('timestamp', '') > last_backup.get('timestamp', ''):
                                    last_backup = backup_data
                            except:
                                pass
                    
                    if last_backup:
                        backup_orders.append({
                            'order_number': order_number,
                            'order_year': order_year,
                            'backup_count': backup_count,
                            'last_backup': last_backup.get('created_at', ''),
                            'items_count': last_backup.get('items_count', 0)
                        })
    
    # Сортируем по номеру заказа
    backup_orders.sort(key=lambda x: (x['order_year'], x['order_number']))
    
    return backup_orders