import sqlite3
import os
from datetime import datetime
from config import APP_DATA_DIR

INVENTORY_DB_FILE = os.path.join(APP_DATA_DIR, 'inventory.db')

def get_connection():
    """Получение соединения с базой склада"""
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(INVENTORY_DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_inventory_db():
    """Инициализация базы склада"""
    conn = get_connection()
    c = conn.cursor()
    
    # Таблица материалов на складе
    c.execute('''CREATE TABLE IF NOT EXISTS materials_stock (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        unit TEXT DEFAULT 'м.п.',
        quantity REAL DEFAULT 0,
        price REAL DEFAULT 0,
        created_at TIMESTAMP,
        updated_at TIMESTAMP
    )''')
    
    # Таблица транзакций (приход/расход/инвентаризация)
    c.execute('''CREATE TABLE IF NOT EXISTS inventory_transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        material_id INTEGER,
        transaction_type TEXT,
        quantity REAL,
        price REAL,
        order_number TEXT,
        order_year INTEGER,
        comment TEXT,
        created_at TIMESTAMP,
        FOREIGN KEY (material_id) REFERENCES materials_stock (id)
    )''')
    
    # Таблица списанных заказов
    c.execute('''CREATE TABLE IF NOT EXISTS deducted_orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT,
        order_year INTEGER,
        deducted_at TIMESTAMP,
        UNIQUE(order_number, order_year)
    )''')
    
    try:
        c.execute('ALTER TABLE inventory_transactions ADD COLUMN comment TEXT')
        print("✅ Добавлен столбец comment")
    except:
        pass  # Столбец уже существует    
    
    conn.commit()
    conn.close()
    print(f"📁 База склада: {INVENTORY_DB_FILE}")

def add_material(name, unit='м.п.', quantity=0, price=0):
    """Добавление материала на склад"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        c.execute('''INSERT INTO materials_stock 
        (name, unit, quantity, price, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?)''',
        (name, unit, quantity, price, now, now))
        
        material_id = c.lastrowid
        
        # Записываем приход
        c.execute('''INSERT INTO inventory_transactions
        (material_id, transaction_type, quantity, price, created_at)
        VALUES (?, 'приход', ?, ?, ?)''',
        (material_id, quantity, price, now))
        
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка добавления материала: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def get_all_materials():
    """Получить все материалы"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM materials_stock ORDER BY name")
    materials = c.fetchall()
    conn.close()
    return [dict(m) for m in materials]

def update_material_quantity(material_id, new_quantity):
    """Обновление количества материала"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    c.execute('''UPDATE materials_stock 
    SET quantity = ?, updated_at = ?
    WHERE id = ?''', (new_quantity, now, material_id))
    
    conn.commit()
    conn.close()

def add_transaction(material_id, transaction_type, quantity, price=0, 
                   order_number=None, order_year=None, comment=''):
    """Добавление транзакции"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    # ✅ ВАЖНО: Проверяем что transaction_type корректный
    if transaction_type not in ['приход', 'расход', 'инвентаризация']:
        print(f"❌ Неверный тип транзакции: {transaction_type}")
        transaction_type = 'приход'
    
    c.execute('''INSERT INTO inventory_transactions
    (material_id, transaction_type, quantity, price, order_number, 
     order_year, comment, created_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)''',
    (material_id, transaction_type, quantity, price, 
     order_number, order_year, comment, now))
    
    conn.commit()
    conn.close()
    print(f"✅ Транзакция добавлена: {transaction_type} {quantity}")

def get_transactions(material_id=None, order_number=None, order_year=None, transaction_type=None):
    """Получение транзакций"""
    conn = get_connection()
    c = conn.cursor()
    
    query = '''SELECT t.*, m.name as material_name 
    FROM inventory_transactions t
    LEFT JOIN materials_stock m ON t.material_id = m.id
    WHERE 1=1'''
    
    params = []
    
    if material_id:
        query += ' AND t.material_id = ?'
        params.append(material_id)
    
    if order_number:
        query += ' AND t.order_number = ?'
        params.append(order_number)
    
    # ✅ ИСПРАВЛЕНО: order_year только для расхода!
    if order_year and transaction_type == 'расход':
        query += ' AND t.order_year = ?'
        params.append(order_year)
    
    if transaction_type:
        query += ' AND t.transaction_type = ?'
        params.append(transaction_type)
    
    query += ' ORDER BY t.created_at DESC'
    
    print(f"🔍 Запрос транзакций: {query}")
    print(f"   Параметры: {params}")
    
    c.execute(query, params)
    transactions = c.fetchall()
    
    print(f"   Найдено транзакций: {len(transactions)}")
    for t in transactions:
        print(f"   - {t['transaction_type']}: {t['material_name']} {t['quantity']}")
    
    conn.close()
    return [dict(t) for t in transactions]

def is_order_deducted(order_number, order_year):
    """Проверка, списан ли заказ"""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''SELECT id FROM deducted_orders 
    WHERE order_number = ? AND order_year = ?''',
    (order_number, order_year))
    
    result = c.fetchone()
    conn.close()
    return result is not None

def mark_order_deducted(order_number, order_year):
    """Отметить заказ как списанный"""
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        c.execute('''INSERT INTO deducted_orders
        (order_number, order_year, deducted_at)
        VALUES (?, ?, ?)''',
        (order_number, order_year, now))
        conn.commit()
        return True
    except Exception as e:
        print(f"❌ Ошибка отметки заказа: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def deduct_order_materials(order_number, order_year, materials):
    """Списание материалов для заказа"""
    if is_order_deducted(order_number, order_year):
        print(f"⚠️ Заказ {order_number} ({order_year}) уже списан!")
        return False
    
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        for material_name, quantity in materials.items():
            # ✅ quantity — это уже метраж/площадь из базы (м.п. или м²)
            c.execute('SELECT id, quantity, unit FROM materials_stock WHERE name = ?',
                     (material_name,))
            row = c.fetchone()
            
            if row:
                material_id = row['id']
                current_qty = row['quantity']
                unit = row['unit']  # ← Получаем единицу измерения
                
                # ✅ СПИСЫВАЕМ КОЛИЧЕСТВО В ПРАВИЛЬНЫХ ЕДИНИЦАХ
                new_quantity = current_qty - quantity
                
                c.execute('''UPDATE materials_stock
                SET quantity = ?, updated_at = ?
                WHERE id = ?''', (new_quantity, now, material_id))
                
                c.execute('''INSERT INTO inventory_transactions
                (material_id, transaction_type, quantity, price,
                order_number, order_year, comment, created_at)
                VALUES (?, 'расход', ?, 0, ?, ?, ?, ?)''',
                (material_id, quantity, order_number, order_year,
                f'Заказ {order_number}', now))
                
                print(f"✅ Списано: {material_name} {quantity} {unit}")
            else:
                print(f"⚠️ Материал '{material_name}' не найден на складе!")
        
        c.execute('''INSERT INTO deducted_orders
        (order_number, order_year, deducted_at)
        VALUES (?, ?, ?)''',
        (order_number, order_year, now))
        
        conn.commit()
        print(f"✅ Заказ {order_number} ({order_year}) списан")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка списания заказа: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def cancel_order_deduction(order_number, order_year):
    """Отмена списания заказа с возвратом материалов на склад"""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute('''SELECT material_id, quantity FROM inventory_transactions
        WHERE transaction_type = 'расход'
        AND order_number = ? AND order_year = ?''',
        (order_number, order_year))
        transactions = c.fetchall()
        
        for trans in transactions:
            material_id = trans['material_id']
            quantity = trans['quantity']
            c.execute('''UPDATE materials_stock
            SET quantity = quantity + ?, updated_at = ?
            WHERE id = ?''',
            (quantity, datetime.now().strftime('%Y-%m-%d %H:%M:%S'), material_id))
        
        c.execute('''DELETE FROM inventory_transactions
        WHERE transaction_type = 'расход'
        AND order_number = ? AND order_year = ?''',
        (order_number, order_year))
        
        c.execute('''DELETE FROM deducted_orders
        WHERE order_number = ? AND order_year = ?''',
        (order_number, order_year))
        
        conn.commit()
        print(f"✅ Списание заказа {order_number} ({order_year}) отменено")
        return True
        
    except Exception as e:
        print(f"❌ Ошибка отмены списания: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

def clear_inventory():
    """Очистка склада (обнуление количества всех материалов)"""
    conn = get_connection()
    c = conn.cursor()
    
    try:
        c.execute("UPDATE materials_stock SET quantity = 0")
        affected = c.rowcount
        conn.commit()
        print(f"✅ Склад очищен: {affected} материалов")
        return affected
    except Exception as e:
        print(f"❌ Ошибка очистки склада: {e}")
        conn.rollback()
        return 0
    finally:
        conn.close()

def get_deducted_materials(order_number, order_year):
    """Получение списка материалов, списанных для заказа"""
    conn = get_connection()
    c = conn.cursor()
    
    c.execute('''SELECT t.*, m.name as material_name, m.unit as material_unit
    FROM inventory_transactions t
    LEFT JOIN materials_stock m ON t.material_id = m.id
    WHERE t.transaction_type = 'расход'
    AND t.order_number = ? AND t.order_year = ?
    ORDER BY t.created_at''',
    (order_number, order_year))
    
    transactions = c.fetchall()
    conn.close()
    
    return [dict(t) for t in transactions]

def get_consumption_report(period='month', start_date=None, end_date=None):
    """Получение отчета по расходу материалов за период
    
    Args:
        period: 'week' - неделя, 'month' - месяц, 'year' - год, 'custom' - произвольный
        start_date: дата начала (для custom)
        end_date: дата конца (для custom)
    """
    from datetime import datetime, timedelta
    
    conn = get_connection()
    c = conn.cursor()
    
    # Определяем дату начала периода
    now = datetime.now()
    
    if period == 'custom' and start_date and end_date:
        # ✅ ПРОИЗВОЛЬНЫЙ ПЕРИОД
        period_name = f"с {start_date.strftime('%d.%m')} по {end_date.strftime('%d.%m.%Y')}"
        start_date_str = start_date.strftime('%Y-%m-%d 00:00:00')
        end_date_str = end_date.strftime('%Y-%m-%d 23:59:59')
    elif period == 'week':
        start_date = now - timedelta(days=7)
        period_name = "за неделю"
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = now.strftime('%Y-%m-%d %H:%M:%S')
    elif period == 'month':
        start_date = now - timedelta(days=30)
        period_name = "за месяц"
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = now.strftime('%Y-%m-%d %H:%M:%S')
    elif period == 'year':
        start_date = now - timedelta(days=365)
        period_name = "за год"
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = now.strftime('%Y-%m-%d %H:%M:%S')
    else:
        start_date = now - timedelta(days=30)
        period_name = "за месяц"
        start_date_str = start_date.strftime('%Y-%m-%d %H:%M:%S')
        end_date_str = now.strftime('%Y-%m-%d %H:%M:%S')
    
    # Получаем расход по материалам
    c.execute('''SELECT m.name, m.unit, 
                        SUM(t.quantity) as total_qty,
                        AVG(t.price) as avg_price,
                        COUNT(t.id) as transaction_count
                FROM inventory_transactions t
                LEFT JOIN materials_stock m ON t.material_id = m.id
                WHERE t.transaction_type = 'расход'
                AND t.created_at >= ?
                AND t.created_at <= ?
                GROUP BY m.name, m.unit
                ORDER BY total_qty DESC''', (start_date_str, end_date_str))
    
    results = c.fetchall()
    conn.close()
    
    report = []
    total_value = 0
    for row in results:
        name = row[0] or 'N/A'
        unit = row[1] or 'м.п.'
        qty = row[2] or 0
        avg_price = row[3] or 0
        count = row[4] or 0
        value = qty * avg_price
        total_value += value
        
        report.append({
            'name': name,
            'unit': unit,
            'quantity': qty,
            'avg_price': avg_price,
            'total_value': value,
            'transaction_count': count
        })
    
    return report, period_name, total_value, start_date, end_date if period == 'custom' else now