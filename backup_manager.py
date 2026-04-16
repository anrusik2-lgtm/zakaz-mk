import os
import shutil
import json
from datetime import datetime
from config import APP_DATA_DIR, INVENTORY_DB_FILE, ORDERS_DB_FILE

# ✅ ИСКЛЮЧАЕМ DB_FILE (базу изделий не бэкапим)
# Папка для бэкапов
BACKUP_DIR = os.path.join(APP_DATA_DIR, 'backups')
os.makedirs(BACKUP_DIR, exist_ok=True)

# ✅ МАКСИМУМ БЭКАПОВ
MAX_AUTO_BACKUPS = 5

def create_backup(backup_type='all', comment='', auto_backup=False):
    """
    Создаёт бэкап базы данных
    
    Args:
        backup_type: 'all' - всё, 'inventory' - только склад, 'orders' - только заказы
        comment: комментарий к бэкапу
        auto_backup: True для автоматических бэкапов (ограничение 5 шт)
    
    Returns:
        Путь к файлу бэкапа или None при ошибке
    """
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_files = []
    
    try:
        # ✅ СКЛАД
        if backup_type in ['all', 'inventory']:
            if os.path.exists(INVENTORY_DB_FILE):
                backup_name = f"inventory_{timestamp}.db"
                backup_path = os.path.join(BACKUP_DIR, backup_name)
                shutil.copy2(INVENTORY_DB_FILE, backup_path)
                backup_files.append({
                    'type': 'inventory',
                    'original': INVENTORY_DB_FILE,
                    'backup': backup_path
                })
                print(f"💾 Бэкап склада: {backup_path}")
        
        # ✅ ЗАКАЗЫ
        if backup_type in ['all', 'orders']:
            if os.path.exists(ORDERS_DB_FILE):
                backup_name = f"orders_{timestamp}.db"
                backup_path = os.path.join(BACKUP_DIR, backup_name)
                shutil.copy2(ORDERS_DB_FILE, backup_path)
                backup_files.append({
                    'type': 'orders',
                    'original': ORDERS_DB_FILE,
                    'backup': backup_path
                })
                print(f"💾 Бэкап заказов: {backup_path}")
        
        # ✅ СОЗДАЁМ МЕТАДАННЫЕ
        metadata = {
            'timestamp': timestamp,
            'created_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'backup_type': backup_type,
            'comment': comment,
            'auto_backup': auto_backup,
            'files': backup_files,
            'files_count': len(backup_files)
        }
        
        metadata_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.json")
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(metadata, f, ensure_ascii=False, indent=2)
        
        print(f"✅ Бэкап создан: {metadata_file}")
        
        # ✅ ОЧИЩАЕМ СТАРЫЕ АВТО-БЭКАПЫ
        if auto_backup:
            cleanup_old_auto_backups()
        
        return metadata_file
    
    except Exception as e:
        print(f"❌ Ошибка создания бэкапа: {e}")
        import traceback
        traceback.print_exc()
        return None

def create_auto_backup_on_open():
    """
    Создаёт автоматический бэкап при ОТКРЫТИИ программы
    """
    try:
        # ✅ Формируем комментарий: "Открытие программы. 01.04.2026 14:30:25"
        now = datetime.now()
        comment = f"Открытие программы. {now.strftime('%d.%m.%Y %H:%M:%S')}"
        
        print(f"\n{'='*70}")
        print(f"🔄 АВТОМАТИЧЕСКИЙ БЭКАП ПРИ ОТКРЫТИИ")
        print(f"   {comment}")
        print(f"{'='*70}\n")
        
        # ✅ Создаём бэкап только склада и заказов
        backup_file = create_backup(
            backup_type='all',  # inventory + orders
            comment=comment,
            auto_backup=True
        )
        
        if backup_file:
            print(f"✅ Авто-бэкап при открытии создан: {backup_file}")
            return True
        else:
            print(f"❌ Не удалось создать авто-бэкап при открытии")
            return False
    
    except Exception as e:
        print(f"❌ Ошибка авто-бэкапа при открытии: {e}")
        import traceback
        traceback.print_exc()
        return False

def create_auto_backup_on_close():
    """
    Создаёт автоматический бэкап при ЗАКРЫТИИ программы
    """
    try:
        # ✅ Формируем комментарий: "Закрытие программы. 01.04.2026 16:30:45"
        now = datetime.now()
        comment = f"Закрытие программы. {now.strftime('%d.%m.%Y %H:%M:%S')}"
        
        print(f"\n{'='*70}")
        print(f"🔄 АВТОМАТИЧЕСКИЙ БЭКАП ПРИ ЗАКРЫТИИ")
        print(f"   {comment}")
        print(f"{'='*70}\n")
        
        # ✅ Создаём бэкап только склада и заказов
        backup_file = create_backup(
            backup_type='all',  # inventory + orders
            comment=comment,
            auto_backup=True
        )
        
        if backup_file:
            print(f"✅ Авто-бэкап при закрытии создан: {backup_file}")
            return True
        else:
            print(f"❌ Не удалось создать авто-бэкап при закрытии")
            return False
    
    except Exception as e:
        print(f"❌ Ошибка авто-бэкапа при закрытии: {e}")
        import traceback
        traceback.print_exc()
        return False

def cleanup_old_auto_backups():
    """
    Удаляет старые автоматические бэкапы, оставляя только последние MAX_AUTO_BACKUPS (5)
    """
    try:
        auto_backups = []
        
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith('backup_') and filename.endswith('.json'):
                filepath = os.path.join(BACKUP_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    
                    # ✅ Проверяем, авто-бэкап ли это
                    if metadata.get('auto_backup', False):
                        mtime = os.path.getmtime(filepath)
                        auto_backups.append((filepath, metadata, mtime))
                except:
                    pass
        
        # ✅ Сортируем по времени (новые сверху)
        auto_backups.sort(key=lambda x: x[2], reverse=True)
        
        # ✅ Удаляем старые, если больше MAX_AUTO_BACKUPS
        deleted_count = 0
        for backup_info in auto_backups[MAX_AUTO_BACKUPS:]:
            filepath, metadata, _ = backup_info
            try:
                # Удаляем файлы бэкапа
                for file_info in metadata.get('files', []):
                    backup_path = file_info.get('backup')
                    if backup_path and os.path.exists(backup_path):
                        os.remove(backup_path)
                        print(f"   🗑️ Удалён старый бэкап: {os.path.basename(backup_path)}")
                
                # Удаляем метаданные
                os.remove(filepath)
                print(f"   🗑️ Удалены метаданные: {os.path.basename(filepath)}")
                deleted_count += 1
            except Exception as e:
                print(f"   ⚠️ Ошибка удаления: {e}")
        
        if deleted_count > 0:
            print(f"🗑️ Удалено {deleted_count} старых авто-бэкапов (осталось {len(auto_backups) - deleted_count})")
        else:
            print(f"✅ Авто-бэкапов: {len(auto_backups)} (лимит: {MAX_AUTO_BACKUPS})")
    
    except Exception as e:
        print(f"⚠️ Ошибка очистки старых бэкапов: {e}")

def get_all_backups():
    """Получает список всех бэкапов"""
    backups = []
    
    try:
        for filename in os.listdir(BACKUP_DIR):
            if filename.startswith('backup_') and filename.endswith('.json'):
                filepath = os.path.join(BACKUP_DIR, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        metadata = json.load(f)
                    backups.append({
                        'filepath': filepath,
                        'timestamp': metadata.get('timestamp', ''),
                        'created_at': metadata.get('created_at', ''),
                        'backup_type': metadata.get('backup_type', 'all'),
                        'comment': metadata.get('comment', ''),
                        'auto_backup': metadata.get('auto_backup', False),
                        'files_count': metadata.get('files_count', 0),
                        'files': metadata.get('files', [])
                    })
                except:
                    pass
        
        # Сортируем по дате (новые сверху)
        backups.sort(key=lambda x: x['timestamp'], reverse=True)
        
    except Exception as e:
        print(f"❌ Ошибка получения списка бэкапов: {e}")
    
    return backups

def restore_backup(backup_filepath):
    """
    Восстанавливает базу из бэкапа
    
    Args:
        backup_filepath: Путь к файлу метаданных бэкапа (.json)
    
    Returns:
        True при успехе, False при ошибке
    """
    if not os.path.exists(backup_filepath):
        print(f"❌ Файл бэкапа не найден: {backup_filepath}")
        return False
    
    try:
        with open(backup_filepath, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        files = metadata.get('files', [])
        if not files:
            print("❌ В бэкапе нет файлов!")
            return False
        
        restored_count = 0
        for file_info in files:
            backup_path = file_info.get('backup')
            original_path = file_info.get('original')
            file_type = file_info.get('type')
            
            if backup_path and os.path.exists(backup_path) and original_path:
                # Копируем бэкап на место оригинала
                shutil.copy2(backup_path, original_path)
                restored_count += 1
                print(f"✅ Восстановлено: {file_type} → {original_path}")
        
        print(f"✅ Восстановление завершено: {restored_count} файлов")
        return True
    
    except Exception as e:
        print(f"❌ Ошибка восстановления: {e}")
        import traceback
        traceback.print_exc()
        return False

def delete_backup(backup_filepath):
    """Удаляет бэкап"""
    try:
        # Читаем метаданные перед удалением
        with open(backup_filepath, 'r', encoding='utf-8') as f:
            metadata = json.load(f)
        
        # Удаляем файлы бэкапа
        for file_info in metadata.get('files', []):
            backup_path = file_info.get('backup')
            if backup_path and os.path.exists(backup_path):
                os.remove(backup_path)
                print(f"🗑️ Удалён файл бэкапа: {backup_path}")
        
        # Удаляем метаданные
        if os.path.exists(backup_filepath):
            os.remove(backup_filepath)
        
        print(f"✅ Бэкап удалён: {backup_filepath}")
        return True
    
    except Exception as e:
        print(f"❌ Ошибка удаления бэкапа: {e}")
        return False

def get_backup_stats():
    """Получает статистику по бэкапам"""
    backups = get_all_backups()
    
    total_size = 0
    database_count = 0
    inventory_count = 0
    orders_count = 0
    auto_backup_count = 0
    manual_backup_count = 0
    
    for backup in backups:
        for file_info in backup.get('files', []):
            backup_path = file_info.get('backup')
            if backup_path and os.path.exists(backup_path):
                total_size += os.path.getsize(backup_path)
            
            file_type = file_info.get('type')
            if file_type == 'database':
                database_count += 1
            elif file_type == 'inventory':
                inventory_count += 1
            elif file_type == 'orders':
                orders_count += 1
        
        # Считаем авто-бэкапы
        if backup.get('auto_backup', False):
            auto_backup_count += 1
        else:
            manual_backup_count += 1
    
    # ✅ ВСЕГДА ВОЗВРАЩАЕМ ВСЕ КЛЮЧИ (даже если 0)
    return {
        'total_backups': len(backups),
        'total_size': total_size,
        'database_count': database_count,  # ← Теперь всегда есть
        'inventory_count': inventory_count,
        'orders_count': orders_count,
        'auto_backup_count': auto_backup_count,
        'manual_backup_count': manual_backup_count
    }