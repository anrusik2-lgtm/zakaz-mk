import sqlite3
import os
from datetime import datetime
from config import ORDERS_DB_FILE, APP_DATA_DIR

def get_connection():
    """Получение соединения с базой заказов в AppData"""
    os.makedirs(APP_DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(ORDERS_DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_orders_db():
    """Инициализация базы заказов в AppData"""
    conn = get_connection()
    c = conn.cursor()
    
    # ✅ ТАБЛИЦА orders С order_year
    c.execute('''CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_number TEXT,
        order_year INTEGER,
        created_at TIMESTAMP,
        updated_at TIMESTAMP,
        color TEXT,
        UNIQUE(order_number, order_year)
    )''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS order_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER,
        name TEXT,
        articul TEXT,
        quantity INTEGER,
        item_number TEXT,
        color TEXT,
        FOREIGN KEY (order_id) REFERENCES orders (id)
    )''')
    
    # ✅ МИГРАЦИЯ: Добавляем order_year в существующие таблицы
    try:
        c.execute('ALTER TABLE orders ADD COLUMN order_year INTEGER')
        print("✅ Добавлен столбец order_year в orders")
    except Exception as e:
        print(f"⚠️ order_year уже существует: {e}")
    
    try:
        c.execute('ALTER TABLE orders ADD COLUMN color TEXT')
        print("✅ Добавлен столбец color в orders")
    except Exception as e:
        print(f"⚠️ color уже существует: {e}")
    
    conn.commit()
    conn.close()
    print(f"📁 База заказов: {ORDERS_DB_FILE}")

def migrate_remove_leading_zeros():
    """Удаляет ведущие нули из номеров заказов во всех таблицах"""
    from config import INVENTORY_DB_FILE
    import sqlite3
    
    updated_count = 0
    
    try:
        # ✅ ПОДКЛЮЧАЕМСЯ К orders.db
        conn_orders = sqlite3.connect(ORDERS_DB_FILE)
        conn_orders.row_factory = sqlite3.Row
        c_orders = conn_orders.cursor()
        
        # ✅ ПОДКЛЮЧАЕМСЯ К inventory.db
        conn_inventory = sqlite3.connect(INVENTORY_DB_FILE)
        conn_inventory.row_factory = sqlite3.Row
        c_inventory = conn_inventory.cursor()
        
        # Получаем все заказы из orders.db
        c_orders.execute("SELECT id, order_number FROM orders")
        orders = c_orders.fetchall()
        
        for order in orders:
            order_id = order['id']
            old_number = order['order_number']
            
            # Убираем ведущие нули
            new_number = old_number.lstrip('0')
            
            # Если номер стал пустым (был "000"), оставляем "0"
            if not new_number:
                new_number = '0'
            
            # Если номер изменился
            if old_number != new_number:
                print(f"🔄 Обновление заказа: {old_number} → {new_number}")
                
                # ✅ Обновляем в orders.db
                c_orders.execute("UPDATE orders SET order_number = ? WHERE id = ?",
                                (new_number, order_id))
                
                # ✅ Обновляем в inventory.db (inventory_transactions)
                c_inventory.execute("""UPDATE inventory_transactions
                                      SET order_number = ?
                                      WHERE order_number = ?""",
                                   (new_number, old_number))
                
                # ✅ Обновляем в inventory.db (deducted_orders)
                c_inventory.execute("""UPDATE deducted_orders
                                      SET order_number = ?
                                      WHERE order_number = ?""",
                                   (new_number, old_number))
                
                updated_count += 1
        
        # ✅ СОХРАНЯЕМ ИЗМЕНЕНИЯ В ОБЕИХ БАЗАХ
        conn_orders.commit()
        conn_inventory.commit()
        
        print(f"✅ Миграция завершена! Обновлено заказов: {updated_count}")
        return updated_count
        
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        return -1
    finally:
        if 'conn_orders' in locals():
            conn_orders.close()
        if 'conn_inventory' in locals():
            conn_inventory.close()

def migrate_orders_to_current_year():
    """✅ Обновляет все заказы без order_year на текущий год"""
    conn = get_connection()
    c = conn.cursor()
    current_year = datetime.now().year
    
    try:
        # Находим заказы без order_year
        c.execute('SELECT id, order_number FROM orders WHERE order_year IS NULL')
        orders_without_year = c.fetchall()
        
        if not orders_without_year:
            print("✅ Все заказы уже имеют год")
            return 0
        
        updated_count = 0
        for order in orders_without_year:
            order_id = order['id']
            order_number = order['order_number']
            
            # Обновляем год
            c.execute('UPDATE orders SET order_year = ? WHERE id = ?',
                     (current_year, order_id))
            updated_count += 1
            print(f"   🔄 Заказ №{order_number} → {current_year}")
        
        conn.commit()
        print(f"✅ Миграция завершена: обновлено {updated_count} заказов")
        return updated_count
    
    except Exception as e:
        print(f"❌ Ошибка миграции: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return -1
    
    finally:
        conn.close()

def save_order(order_number, items, color="", order_year=None):
    """Сохранение заказа с поддержкой года"""
    if not order_number or not items:
        return None
    
    conn = get_connection()
    c = conn.cursor()
    
    # ✅ Если год не указан, определяем по текущей дате
    if order_year is None:
        order_year = datetime.now().year
    
    try:
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # ✅ ПРОВЕРЯЕМ ПО order_number + order_year
        c.execute("SELECT id FROM orders WHERE order_number = ? AND order_year = ?", 
                 (order_number, order_year))
        existing = c.fetchone()
        
        if existing:
            order_id = existing['id']
            c.execute("DELETE FROM order_items WHERE order_id = ?", (order_id,))
            c.execute("UPDATE orders SET updated_at = ?, color = ? WHERE id = ?", 
                     (now, color, order_id))
        else:
            c.execute('''INSERT INTO orders 
                        (order_number, order_year, created_at, updated_at, color) 
                        VALUES (?, ?, ?, ?, ?)''', 
                     (order_number, order_year, now, now, color))
            order_id = c.lastrowid
        
        for item in items:
            c.execute('''INSERT INTO order_items 
                        (order_id, name, articul, quantity, item_number, color) 
                        VALUES (?, ?, ?, ?, ?, ?)''', 
                     (order_id, item['name'], item['articul'], 
                      item['qty'], item.get('item_number', ''), 
                      item.get('color', '')))
        
        conn.commit()
        return order_id
    
    except Exception as e:
        print(f"❌ Ошибка сохранения заказа: {e}")
        import traceback
        traceback.print_exc()
        conn.rollback()
        return None
    
    finally:
        conn.close()

def get_order(order_number, order_year=None):
    """✅ Получение заказа по номеру и году"""
    conn = get_connection()
    c = conn.cursor()
    
    # ✅ Если год не указан, определяем по текущей дате
    if order_year is None:
        order_year = datetime.now().year
    
    # ✅ ИСПРАВЛЕНО: поиск по order_number + order_year
    c.execute("SELECT * FROM orders WHERE order_number = ? AND order_year = ?", 
             (order_number, order_year))
    order = c.fetchone()
    
    if order:
        c.execute("SELECT * FROM order_items WHERE order_id = ?", (order['id'],))
        items = []
        for row in c.fetchall():
            items.append({
                'name': row['name'],
                'articul': row['articul'],
                'qty': row['quantity'],
                'item_number': row['item_number'] if row['item_number'] else '',
                'color': row['color'] if row['color'] else ''
            })
        order = dict(order)
        order['items'] = items
    else:
        order = None
    
    conn.close()
    return order

def get_all_orders():
    """Получение всех заказов"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
        SELECT o.*, COUNT(oi.id) as items_count
        FROM orders o
        LEFT JOIN order_items oi ON o.id = oi.order_id
        GROUP BY o.id
        ORDER BY o.updated_at DESC
    """)
    orders = c.fetchall()
    conn.close()
    return [dict(o) for o in orders]

def clear_orders():
    """Очистка всех заказов"""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM order_items")
    c.execute("DELETE FROM orders")
    conn.commit()
    conn.close()

def delete_order(order_number, order_year=None):
    """Удаление заказа по номеру и году"""
    conn = get_connection()
    c = conn.cursor()
    
    # ✅ Если год не указан, берём текущий
    if order_year is None:
        order_year = datetime.now().year
    
    c.execute("SELECT id FROM orders WHERE order_number = ? AND order_year = ?", 
             (order_number, order_year))
    order = c.fetchone()
    
    if order:
        c.execute("DELETE FROM order_items WHERE order_id = ?", (order['id'],))
        c.execute("DELETE FROM orders WHERE id = ?", (order['id'],))
        conn.commit()
    
    conn.close()