import sqlite3
import os
import pandas as pd
from datetime import datetime
from config import DB_FILE, APP_DATA_DIR

PASSWORD = "2001884"
EMPTY_MARKER = "###EMPTY###"

def get_connection():
    """Возвращает соединение с БД в AppData"""
    try:
        os.makedirs(APP_DATA_DIR, exist_ok=True)
        conn = sqlite3.connect(DB_FILE)
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except Exception as e:
        print(f"❌ Ошибка подключения к базе: {e}")
        temp_db = os.path.join(os.environ['TEMP'], 'ZakazMK', 'database.db')
        os.makedirs(os.path.dirname(temp_db), exist_ok=True)
        return sqlite3.connect(temp_db)

def init_db():
    """Инициализация базы данных"""
    try:
        conn = get_connection()
        c = conn.cursor()
        
        # ✅ СОЗДАЕМ ТАБЛИЦУ, ЕСЛИ ЕЁ НЕТ
        c.execute('''CREATE TABLE IF NOT EXISTS items
        (id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT,
        articul TEXT,
        detail TEXT,
        size REAL,
        quantity INTEGER,
        material TEXT,
        consumption REAL,
        furniture TEXT,
        furniture_qty INTEGER)''')
        
        conn.commit()
        
        # Проверяем, есть ли записи
        c.execute("SELECT COUNT(*) FROM items")
        count = c.fetchone()[0]
        conn.close()
        
        print(f"📊 База данных: {DB_FILE}")
        print(f"📊 Записей в базе: {count}")
        return True
    except Exception as e:
        print(f"❌ Ошибка инициализации базы: {e}")
        return False

def safe_str(value):
    if value is None or pd.isna(value):
        return ''
    text = str(value).strip()
    if text == EMPTY_MARKER:
        return ''
    return text

def safe_int(value):
    try:
        if value is None or pd.isna(value):
            return 0
        text = str(value).strip()
        if text == EMPTY_MARKER or text == '' or text.lower() in ['nan', 'none', '0']:
            return 0
        if any(c.isalpha() for c in text):
            return 0
        return int(float(text.replace(',', '.')))
    except:
        return 0

def safe_float(value):
    try:
        if value is None or pd.isna(value):
            return 0.0
        text = str(value).strip()
        if text == EMPTY_MARKER or text == '' or text.lower() in ['nan', 'none', '0']:
            return 0.0
        if any(c.isalpha() for c in text):
            return 0.0
        return float(text.replace(',', '.'))
    except:
        return 0.0

def import_from_excel(filepath, password):
    """Импорт данных из Excel в базу в AppData"""
    from datetime import datetime  # ← Импортируем внутри функции
    from inventory_db import init_inventory_db, add_material, get_all_materials, update_material_quantity
    
    if password != PASSWORD:
        print("❌ Неверный пароль!")
        return False
    
    try:
        print(f"📖 Чтение файла: {filepath}")
        print(f"📂 База данных: {DB_FILE}")
        
        # Инициализируем базу перед импортом
        init_db()
        
        # ✅ ИНИЦИАЛИЗИРУЕМ БАЗУ СКЛАДА
        init_inventory_db()
        
        xl = pd.ExcelFile(filepath)
        print(f"📑 Листы в файле: {xl.sheet_names}")
        
        # ========== ЛИСТ 1: БАЗА ИЗДЕЛИЙ ==========
        if 'База' in xl.sheet_names:
            df = pd.read_excel(filepath, sheet_name='База', header=0)
            print(f"📊 Прочитано строк в листе 'База': {len(df)}")
            
            conn = get_connection()
            c = conn.cursor()
            
            c.execute('DELETE FROM items')
            print("🗑️ Таблица изделий очищена")
            
            last_name = ''
            last_articul = ''
            imported_count = 0
            skipped_count = 0
            
            # Список для сбора уникальных материалов из базы
            materials_from_items = {}
            
            for index, row in df.iterrows():
                try:
                    name = safe_str(row.iloc[0]) if len(row) > 0 else ''
                    articul = safe_str(row.iloc[1]) if len(row) > 1 else ''
                    detail = safe_str(row.iloc[2]) if len(row) > 2 else ''
                    size = safe_float(row.iloc[3]) if len(row) > 3 else 0.0
                    quantity = safe_int(row.iloc[4]) if len(row) > 4 else 0
                    material = safe_str(row.iloc[5]) if len(row) > 5 else ''
                    consumption = safe_float(row.iloc[6]) if len(row) > 6 else 0.0
                    furniture = safe_str(row.iloc[7]) if len(row) > 7 else ''
                    furniture_qty = safe_int(row.iloc[8]) if len(row) > 8 else 0
                    
                    if 'Наименование' in name or not name:
                        skipped_count += 1
                        continue
                    
                    if not name:
                        name = last_name
                        articul = last_articul if articul == '' else articul
                    else:
                        last_name = name
                        last_articul = articul
                    
                    if material or furniture or detail:
                        c.execute('''INSERT INTO items
                        (name, articul, detail, size, quantity, material,
                        consumption, furniture, furniture_qty)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                        (name, articul, detail, size, quantity, material,
                        consumption, furniture, furniture_qty))
                        imported_count += 1
                        
                        # ✅ СОБИРАЕМ МАТЕРИАЛЫ ИЗ БАЗЫ
                        if material and material not in materials_from_items:
                            materials_from_items[material] = True
                    else:
                        skipped_count += 1
                        
                except Exception as row_error:
                    print(f"❌ Ошибка в строке {index+2}: {row_error}")
                    skipped_count += 1
                    continue
            
            conn.commit()
            
            c.execute("SELECT COUNT(*) FROM items")
            final_count = c.fetchone()[0]
            conn.close()
            
            print(f"\n✅ Импортировано изделий: {imported_count}")
            print(f"⏭️ Пропущено: {skipped_count}")
            print(f"📊 Всего в базе: {final_count}")
        
        # ========== ЛИСТ 2: МАТЕРИАЛЫ СКЛАДА ==========
        if 'Материал' in xl.sheet_names:
            print(f"\n📦 Импорт материалов со склада...")
            df_materials = pd.read_excel(filepath, sheet_name='Материал', header=0)
            print(f"📊 Прочитано строк в листе 'Материал': {len(df_materials)}")
            
            # Получаем существующие материалы на складе
            existing_materials = {m['name']: m for m in get_all_materials()}
            
            updated_count = 0
            added_count = 0
            
            for index, row in df_materials.iterrows():
                try:
                    mat_name = safe_str(row.iloc[0]) if len(row) > 0 else ''
                    mat_unit = safe_str(row.iloc[1]) if len(row) > 1 else 'м.п.'
                    mat_qty = safe_float(row.iloc[2]) if len(row) > 2 else 0
                    mat_price = safe_float(row.iloc[3]) if len(row) > 3 else 0
                    
                    if not mat_name or 'Наименование' in mat_name:
                        continue
                    
                    # ✅ КОНВЕРТИРУЕМ ЕДИНИЦЫ ИЗМЕРЕНИЯ
                    mat_unit = convert_unit_to_superscript(mat_unit)
                    
                    from inventory_db import get_connection as get_inv_connection
                    conn_inv = get_inv_connection()
                    c_inv = conn_inv.cursor()
                    
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    
                    if mat_name in existing_materials:
                        # ✅ ОБНОВЛЯЕМ СУЩЕСТВУЮЩИЙ МАТЕРИАЛ
                        c_inv.execute('''UPDATE materials_stock 
                        SET unit = ?, quantity = ?, price = ?, updated_at = ?
                        WHERE name = ?''',
                        (mat_unit, mat_qty, mat_price, now, mat_name))
                        updated_count += 1
                        print(f"   🔄 Обновлён: {mat_name} ({mat_qty} {mat_unit}, {mat_price} ₽)")
                    else:
                        # ✅ ДОБАВЛЯЕМ НОВЫЙ МАТЕРИАЛ
                        c_inv.execute('''INSERT INTO materials_stock 
                        (name, unit, quantity, price, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?)''',
                        (mat_name, mat_unit, mat_qty, mat_price, now, now))
                        added_count += 1
                        print(f"   ➕ Добавлен: {mat_name} ({mat_qty} {mat_unit}, {mat_price} ₽)")
                    
                    conn_inv.commit()
                    conn_inv.close()
                    
                except Exception as e:
                    print(f"❌ Ошибка импорта материала строка {index+2}: {e}")
                    continue
            
            print(f"\n✅ Материалы обновлены: {updated_count}")
            print(f"✅ Материалы добавлены: {added_count}")
        
        # ========== ДОБАВЛЯЕМ МАТЕРИАЛЫ ИЗ БАЗЫ В СКЛАД (ЕСЛИ НЕТ) ==========
        if materials_from_items:
            print(f"\n📦 Добавляем {len(materials_from_items)} материалов из базы в склад...")
            
            from inventory_db import get_connection as get_inv_connection
            conn_inv = get_inv_connection()
            c_inv = conn_inv.cursor()
            
            # Получаем актуальный список после импорта
            c_inv.execute('SELECT name FROM materials_stock')
            existing_names = {row[0] for row in c_inv.fetchall()}
            
            added_from_items = 0
            for mat_name in materials_from_items:
                if mat_name not in existing_names:
                    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    c_inv.execute('''INSERT INTO materials_stock 
                    (name, unit, quantity, price, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                    (mat_name, 'м.п.', 0, 0, now, now))
                    added_from_items += 1
                    print(f"   ➕ {mat_name}")
            
            conn_inv.commit()
            conn_inv.close()
            print(f"✅ Добавлено {added_from_items} материалов из базы")
        
        return True
        
    except Exception as e:
        print(f"❌ Ошибка импорта: {e}")
        import traceback
        traceback.print_exc()
        return False


def convert_unit_to_superscript(unit):
    """Конвертирует единицы измерения в верхний регистр для цифр"""
    if not unit:
        return 'м.п.'
    
    # ✅ ЗАМЕНА: м2 → м², м3 → м³, см2 → см² и т.д.
    replacements = {
        'м2': 'м²', 'м3': 'м³',
        'см2': 'см²', 'см3': 'см³',
        'мм2': 'мм²', 'мм3': 'мм³',
        'км2': 'км²',
    }
    
    result = unit
    for old, new in replacements.items():
        result = result.replace(old, new)
    
    return result

def import_nonstandard_from_excel(filepath, order_number):
    """Импорт нестандартных изделий из Excel (БЕЗ пароля)"""
    try:
        print(f"📖 Чтение файла: {filepath}")
        # ✅ ИНИЦИАЛИЗИРУЕМ БАЗУ
        init_db()
        
        # ✅ ОПРЕДЕЛЯЕМ ТИП ФАЙЛА И ВЫБИРАЕМ ДВИЖОК
        import os
        file_ext = os.path.splitext(filepath)[1].lower()
        
        if file_ext == '.xls':
            # Для старых .xls файлов используем xlrd
            df = pd.read_excel(filepath, engine='xlrd', header=None)
            print(f"📊 Чтение через xlrd (.xls формат)")
        else:
            # Для .xlsx используем openpyxl
            df = pd.read_excel(filepath, engine='openpyxl', header=None)
            print(f"📊 Чтение через openpyxl (.xlsx формат)")
        
        # Выводим содержимое для отладки
        print("\n" + "="*60)
        print("СОДЕРЖИМОЕ EXCEL ФАЙЛА:")
        print("="*60)
        for idx, row in df.iterrows():
            values = []
            for i in range(min(6, len(row))):
                val = row.iloc[i] if i < len(row) else ''
                values.append(f"{val}")
            print(f"Строка {idx}: A='{values[0]}' | B='{values[1]}' | C='{values[2]}' | D={values[3]} | E={values[4]} | F={values[5]}")
        print("="*60 + "\n")
        
        conn = get_connection()
        c = conn.cursor()
        
        # Словарь для хранения данных
        items_dict = {}
        current_item_key = None
        current_section = ''
        current_item_name = None
        
        # ✅ СЧЁТЧИКИ ДЛЯ СТАТИСТИКИ
        imported_count = 0
        failed_items = []
        
        for index, row in df.iterrows():
            try:
                cell_a = safe_str(row.iloc[0]) if len(row) > 0 else ''
                cell_b = safe_str(row.iloc[1]) if len(row) > 1 else ''
                cell_c = safe_str(row.iloc[2]) if len(row) > 2 else ''
                try:
                    cell_d = float(row.iloc[3]) if len(row) > 3 and pd.notna(row.iloc[3]) else 0
                except:
                    cell_d = 0
                try:
                    cell_e = float(row.iloc[4]) if len(row) > 4 and pd.notna(row.iloc[4]) else 0
                except:
                    cell_e = 0
                try:
                    cell_f = float(row.iloc[5]) if len(row) > 5 and pd.notna(row.iloc[5]) else 0
                except:
                    cell_f = 0
                
                # Поиск изделия (строка "Изделие")
                if cell_a.lower() == 'изделие' and cell_b:
                    current_item_name = cell_b
                    current_item_key = cell_b  # ✅ Ключ без номера заказа
                    if current_item_key not in items_dict:
                        items_dict[current_item_key] = {
                            'name': cell_b,
                            'order': order_number,
                            'materials': [],
                            'furniture': []
                        }
                    print(f"📦 Найдено изделие: {cell_b}")
                    current_section = ''
                    continue
                
                # Поиск секции материалов
                if 'спецификация на панели и профили' in cell_a.lower():
                    current_section = 'material'
                    print(f"   📐 Найдена секция материалов")
                    continue
                
                # Поиск секции фурнитуры
                if 'спецификация на фурнитуру' in cell_a.lower():
                    current_section = 'furniture'
                    print(f"   🔧 Найдена секция фурнитуры")
                    continue
                
                # Обработка материалов
                if current_section == 'material' and current_item_key:
                    if str(cell_a).lower() in ['№', 'номер', 'наименование материала']:
                        continue
                    if cell_b and cell_c and cell_d > 0:
                        material_name = cell_b
                        part_name = cell_c
                        length = cell_d
                        width = cell_e if cell_e > 0 else 0
                        qty = int(cell_f) if cell_f > 0 else 1
                        items_dict[current_item_key]['materials'].append({
                            'material': material_name,
                            'part': part_name,
                            'length': length,
                            'width': width,
                            'qty': qty
                        })
                        if width > 0:
                            print(f"      ➕ Материал: {part_name} ({material_name}) {int(length)}x{int(width)}мм x{qty}")
                        else:
                            print(f"      ➕ Материал: {part_name} ({material_name}) {int(length)}мм x{qty}")
                
                # Обработка фурнитуры
                if current_section == 'furniture' and current_item_key:
                    if str(cell_a).lower() in ['№', 'номер']:
                        continue
                    if cell_b and cell_b.lower() not in ['наименование', 'кол-во']:
                        furn_name = cell_b
                        qty = 1
                        if cell_c:
                            try:
                                qty_str = str(cell_c).strip().replace(',', '.')
                                qty = int(float(qty_str))
                            except:
                                qty = 1
                        if qty > 0:
                            items_dict[current_item_key]['furniture'].append({
                                'name': furn_name,
                                'qty': qty
                            })
                            print(f"      🔧 Фурнитура: {furn_name} x{qty} шт.")
                            
            except Exception as row_error:
                print(f"   ⚠️ Ошибка в строке {index}: {row_error}")
                continue
        
        # Сохраняем в базу
        saved_items = []
        for item_key, item_data in items_dict.items():
            if item_data['materials'] or item_data['furniture']:
                try:
                    db_name = f"[НЕСТАНДАРТ] {item_data['name']}"
                    saved_items.append(db_name)
                    
                    # Удаляем старые записи
                    c.execute("DELETE FROM items WHERE name = ? AND articul = ?",
                             (db_name, 'см.рис.'))
                    
                    # ✅ АГРЕГИРУЕМ МАТЕРИАЛЫ - суммируем одинаковые
                    aggregated_materials = {}
                    for mat in item_data['materials']:
                        if mat['part'] and mat['qty'] > 0:
                            # Создаем ключ из названия детали и материала
                            key = (mat['part'], mat['material'], mat['width'])
                            if key in aggregated_materials:
                                # Если такой материал уже есть - суммируем количество и расход
                                aggregated_materials[key]['qty'] += mat['qty']
                                # Расход пересчитываем
                                if mat['width'] > 0:
                                    # Для площадных материалов
                                    aggregated_materials[key]['consumption'] += (mat['length'] * mat['width'] / 1000000.0) * mat['qty']
                                else:
                                    # Для погонных материалов (переводим мм в метры)
                                    aggregated_materials[key]['consumption'] += (mat['length'] / 1000.0) * mat['qty']
                            else:
                                # Первый раз встречаем этот материал
                                if mat['width'] > 0:
                                    consumption = (mat['length'] * mat['width'] / 1000000.0) * mat['qty']
                                else:
                                    consumption = (mat['length'] / 1000.0) * mat['qty']
                                aggregated_materials[key] = {
                                    'part': mat['part'],
                                    'material': mat['material'],
                                    'length': mat['length'],
                                    'width': mat['width'],
                                    'qty': mat['qty'],
                                    'consumption': consumption
                                }
                    
                    # Сохраняем агрегированные материалы
                    for key, mat in aggregated_materials.items():
                        if mat['width'] > 0:
                            size_str = f"{int(mat['length'])}x{int(mat['width'])}"
                        else:
                            size_str = str(int(mat['length']))
                        c.execute('''INSERT INTO items
                            (name, articul, detail, size, quantity, material,
                            consumption, furniture, furniture_qty)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                            (db_name, 'см.рис.', mat['part'], size_str, int(mat['qty']),
                            mat['material'], mat['consumption'], '', 0))
                        if mat['width'] > 0:
                            print(f"      💾 Сохранен материал: {mat['part']} ({mat['material']}) {int(mat['length'])}x{int(mat['width'])}мм x{mat['qty']} (расход: {mat['consumption']:.3f} м²)")
                        else:
                            print(f"      💾 Сохранен материал: {mat['part']} ({mat['material']}) {int(mat['length'])}мм x{mat['qty']} (расход: {mat['consumption']:.3f} м)")
                    
                    # Сохраняем фурнитуру
                    for furn in item_data['furniture']:
                        if furn['name'] and furn['qty'] > 0:
                            c.execute('''INSERT INTO items
                                (name, articul, detail, size, quantity, material,
                                consumption, furniture, furniture_qty)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                                (db_name, 'см.рис.', '', 0, 1,
                                '', 0, furn['name'], int(furn['qty'])))
                            print(f"      💾 Сохранена фурнитура: {furn['name']} x{furn['qty']}")
                    
                    print(f"\n✅ Сохранено изделие: {db_name}")
                    print(f"   - Материалов: {len(aggregated_materials)} (после агрегации)")
                    print(f"   - Фурнитуры: {len(item_data['furniture'])}")
                    imported_count += 1
                    
                except Exception as e:
                    print(f"❌ Ошибка сохранения изделия {item_key}: {e}")
                    failed_items.append(item_key)
        
        conn.commit()
        conn.close()
        
        # ✅ ВОЗВРАЩАЕМ СТАТИСТИКУ
        if saved_items:
            print(f"\n✅ ИМПОРТ ЗАВЕРШЁН!")
            print(f"   Успешно импортировано: {imported_count} из {len(items_dict)}")
            if failed_items:
                print(f"   Не импортировано: {len(failed_items)}")
                for item in failed_items:
                    print(f"      ❌ {item}")
            return saved_items[0] if saved_items else False, imported_count, len(items_dict), failed_items
        else:
            return False, 0, len(items_dict), list(items_dict.keys())
            
    except Exception as e:
        print(f"❌ Ошибка импорта нестандартных: {e}")
        import traceback
        traceback.print_exc()
        return False, 0, 0, []

def search_items_by_articul(articul):
    """Поиск изделий по артикулу (точное совпадение)"""
    if not articul or len(articul) < 2:
        return []
    try:
        init_db()
        conn = get_connection()
        c = conn.cursor()
        
        # Точный поиск по артикулу
        c.execute("""
        SELECT name, articul FROM items
        WHERE articul = ? OR articul LIKE ? OR articul LIKE ?
        ORDER BY name LIMIT 10
        """, (articul, f'%{articul}%', f'{articul}%'))
        
        results = c.fetchall()
        conn.close()
        print(f"🔍 Поиск по артикулу '{articul}': найдено {len(results)} результатов")
        return results
    except Exception as e:
        print(f"❌ Ошибка поиска по артикулу: {e}")
        return []

def search_items(query):
    """Поиск изделий по названию или артикулу"""
    if not query or len(query) < 2:
        return []
    try:
        # ✅ УБЕДИМСЯ, ЧТО БАЗА ИНИЦИАЛИЗИРОВАНА
        init_db()
        
        conn = get_connection()
        c = conn.cursor()
        c.execute("""
        SELECT name, articul FROM items
        WHERE name LIKE ? OR articul LIKE ?
        ORDER BY name LIMIT 50
        """, (f'%{query}%', f'%{query}%'))
        results = c.fetchall()
        conn.close()
        print(f"🔍 Поиск '{query}': найдено {len(results)} результатов")
        return results
    except Exception as e:
        print(f"❌ Ошибка поиска: {e}")
        import traceback
        traceback.print_exc()
        return []

def get_item_details(name, articul):
    """Получение деталей изделия"""
    try:
        # ✅ УБЕДИМСЯ, ЧТО БАЗА ИНИЦИАЛИЗИРОВАНА
        init_db()
        
        conn = get_connection()
        c = conn.cursor()
        c.execute('''SELECT detail, size, quantity, material, consumption, furniture, furniture_qty
        FROM items WHERE name = ? AND articul = ?''', (name, articul))
        results = c.fetchall()
        conn.close()
        return results
    except Exception as e:
        print(f"❌ Ошибка получения деталей: {e}")
        return []

def get_materials_for_item(name, articul):
    """Получение материалов и фурнитуры для изделия"""
    try:
        init_db()
        conn = get_connection()
        c = conn.cursor()
        print(f"🔍 Поиск материалов для: '{name}' с артикулом '{articul}'")
        
        # Для нестандартных изделий
        if articul in ['нестандарт', 'см.рис.', 'см. рис.'] or name.startswith('[НЕСТАНДАРТ]'):
            # ✅ ИСПРАВЛЕНО: проверяем оба поля - и consumption, и quantity
            c.execute('''SELECT material, COALESCE(NULLIF(consumption, 0), quantity) as qty
            FROM items
            WHERE name = ? AND material != '' AND material IS NOT NULL 
            AND (consumption > 0 OR quantity > 0)''',
            (name,))
            materials = c.fetchall()
            c.execute('''SELECT furniture, furniture_qty FROM items
            WHERE name = ? AND furniture != '' AND furniture IS NOT NULL AND furniture_qty > 0''',
            (name,))
            furniture = c.fetchall()
        else:
            # Для стандартных изделий
            c.execute('''SELECT material, consumption FROM items
            WHERE articul = ? AND material != '' AND material IS NOT NULL AND consumption > 0''',
            (articul,))
            materials = c.fetchall()
            c.execute('''SELECT furniture, furniture_qty FROM items
            WHERE articul = ? AND furniture != '' AND furniture IS NOT NULL AND furniture_qty > 0''',
            (articul,))
            furniture = c.fetchall()
        
        conn.close()
        print(f"📊 Результаты для '{name}':")
        print(f"   - Материалов: {len(materials)}")
        for i, mat in enumerate(materials):
            print(f"     {i+1}. {mat[0]}: {mat[1]} м")
        print(f"   - Фурнитуры: {len(furniture)}")
        for i, f in enumerate(furniture):
            print(f"     {i+1}. {f[0]}: {f[1]} шт.")
        return materials, furniture
    except Exception as e:
        print(f"❌ Ошибка получения материалов: {e}")
        return [], []