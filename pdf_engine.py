from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import datetime
from config import PDF_OUTPUT_DIR

# === РЕГИСТРАЦИЯ КИРИЛЛИЧЕСКОГО ШРИФТА ===
def register_cyrillic_font():
    """Регистрирует шрифт с поддержкой кириллицы"""
    try:
        font_paths = [
            r"C:\Windows\Fonts\arial.ttf",
            r"C:\Windows\Fonts\Arial.ttf",
            os.path.join(os.environ.get('WINDIR', 'C:\\Windows'), 'Fonts', 'arial.ttf')
        ]
        for font_path in font_paths:
            if os.path.exists(font_path):
                pdfmetrics.registerFont(TTFont('Arial', font_path))
                return 'Arial'
        return 'Helvetica'
    except:
        return 'Helvetica'

CYRILLIC_FONT = register_cyrillic_font()

def add_page_header(canvas, doc, order_number, page_num, total_pages):
    """Добавляет верхний и нижний колонтитулы на страницу"""
    from reportlab.lib.colors import black
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
    # Сохраняем состояние
    canvas.saveState()
    
    # ✅ ВЕРХНИЙ КОЛОНТИТУЛ (справа)
    canvas.setFont(CYRILLIC_FONT, 9)
    canvas.drawRightString(doc.pagesize[0] - 20*mm, doc.pagesize[1] - 15*mm, 
                          f"Заказ № {order_number}")
    
    # ✅ НИЖНИЙ КОЛОНТИТУЛ (справа) - номер страницы
    canvas.setFont(CYRILLIC_FONT, 8)
    canvas.drawRightString(doc.pagesize[0] - 20*mm, 15*mm, 
                          f"Лист {page_num} из {total_pages}")
    
    # Восстанавливаем состояние
    canvas.restoreState()

def create_order_pdf(order_number, order_items, materials, furniture, output_folder=None, include_summary=False):
    """Создаёт PDF файл заказа
    
    Args:
        include_summary: если True, добавляет общий отчет и карты раскроя
    """
    from config import PDF_OUTPUT_DIR
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.graphics.shapes import Drawing, Rect, String, Group
    import os
    import datetime
    
    from config import PDF_OUTPUT_DIR, load_config
    
    # ✅ ЗАГРУЖАЕМ КОНФИГ ДЛЯ ПОЛУЧЕНИЯ НАСТРОЕК РАСКРОЯ
    config = load_config()
    stock_length = config.get('cutting_stock_length', 6000)  # Длина хлыста из конфига
    kerf_width = config.get('kerf_width', 3)  # ✅ Толщина реза из конфига (по умолчанию 3мм)
    show_cutting = config.get('show_cutting_maps', False)
    
    print(f"\n{'='*60}")
    print(f"🔍 CREATE_ORDER_PDF:")
    print(f"   include_summary (передано): {include_summary}")
    print(f"   Длина хлыста для раскроя: {stock_length}мм ({stock_length/1000:.1f}м)")
    print(f"   Толщина реза (пропил): {kerf_width}мм")
    print(f"   Показывать раскрой (из конфига): {show_cutting}")
    print(f"{'='*60}\n")
    
    if output_folder is None:
        output_folder = PDF_OUTPUT_DIR
    
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)
    
    filename = f"Заказ_{order_number}.pdf"
    filepath = os.path.join(output_folder, filename)
    
    doc = SimpleDocTemplate(
        filepath,
        pagesize=A4,
        rightMargin=10*mm,
        leftMargin=10*mm,
        topMargin=25*mm,
        bottomMargin=25*mm
    )
    
    # Стили
    title_style = ParagraphStyle('Title', fontName=CYRILLIC_FONT, fontSize=14, alignment=TA_CENTER, spaceAfter=8, leading=16)
    header_style = ParagraphStyle('Header', fontName=CYRILLIC_FONT, fontSize=12, alignment=TA_CENTER, spaceAfter=5, leading=14)
    normal_style = ParagraphStyle('Normal', fontName=CYRILLIC_FONT, fontSize=10, alignment=TA_LEFT, leading=12)
    label_style = ParagraphStyle('Label', fontName=CYRILLIC_FONT, fontSize=9, alignment=TA_RIGHT, leading=11)
    cell_style_center = ParagraphStyle('CellCenter', fontName=CYRILLIC_FONT, fontSize=9, alignment=TA_CENTER, leading=11)
    cell_style_left = ParagraphStyle('CellLeft', fontName=CYRILLIC_FONT, fontSize=9, alignment=TA_LEFT, leading=11)
    
    elements = []
    from database import get_item_details, get_materials_for_item
    
    print("\n" + "="*70)
    print("🔍 CREATE_ORDER_PDF - ПОЛУЧЕНЫ ПАРАМЕТРЫ:")
    print(f"   order_number: {order_number}")
    print(f"   order_items: {len(order_items)} позиций")
    print(f"   materials: {dict(materials) if materials else 'пусто'}")
    print(f"   furniture: {dict(furniture) if furniture else 'пусто'}")
    print(f"   output_folder: {output_folder}")
    print(f"   include_summary: {include_summary}")
    print("="*70 + "\n")
    
    # === ПО КАЖДОМУ ИЗДЕЛИЮ ===
    for idx, item in enumerate(order_items, 1):
        print(f"\n📄 Обработка изделия {idx}: {item['name']}")
        
        # === ЗАГОЛОВОК С НОМЕРОМ ЗАКАЗА И ПОЗИЦИЕЙ ===
        elements.append(Paragraph(f"ЗАКАЗ № {order_number} / Позиция: {item.get('item_number', '')}", title_style))
        elements.append(Spacer(1, 5))
        
        display_articul = item['articul']
        if display_articul == 'нестандарт':
            display_articul = 'см. рис.'
        
        # Информация об изделии
        data = [
            [Paragraph("<b>Наименование:</b>", label_style), Paragraph(item['name'], normal_style)],
            [Paragraph("<b>Артикул:</b>", label_style), Paragraph(display_articul, normal_style)],
            [Paragraph("<b>Количество:</b>", label_style), Paragraph(f"{item['qty']} шт.", normal_style)],
            [Paragraph("<b>Цвет:</b>", label_style), Paragraph(item.get('color', ''), normal_style)]
        ]
        
        info_table = Table(data, colWidths=[30*mm, 130*mm])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT),
            ('FONTSIZE', (0, 0), (0, -1), 9),
            ('FONTSIZE', (1, 0), (1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 2),
            ('TOPPADDING', (0, 0), (-1, -1), 2),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ]))
        
        elements.append(info_table)
        elements.append(Spacer(1, 8))
        
        # === СПЕЦИФИКАЦИЯ НА ИЗДЕЛИЕ ===
        details = get_item_details(item['name'], item['articul'])
        if details:
            elements.append(Paragraph("<b>СПЕЦИФИКАЦИЯ НА ИЗДЕЛИЕ</b>", title_style))
            elements.append(Spacer(1, 3))
            
            details_data = [[
                Paragraph('Деталь', cell_style_center),
                Paragraph('Размер (мм)', cell_style_center),
                Paragraph('Кол-во в изд.', cell_style_center),
                Paragraph('Кол-во в заказе', cell_style_center),
                Paragraph('Нарезать (м)', cell_style_center),
                Paragraph('Материал', cell_style_center)
            ]]
            
            seen_rows = set()
            
            for detail in details:
                detail_name = (detail[0] or '').strip()
                size = detail[1] if detail[1] else 0
                qty_per_item = detail[2] if detail[2] else 0
                material = (detail[3] or '').strip()
                
                if not detail_name and not material:
                    continue
                if detail_name.lower() in ['№', 'заказ', 'наименование', 'деталь']:
                    continue
                
                size_str = str(int(size)) if isinstance(size, float) and size.is_integer() else str(size)
                
                # ✅ РАСЧЁТ: Размер (мм) × Кол-во в изд. × Кол-во изделий / 1000 = метры
                try:
                    size_num = float(size) if size else 0
                    cut_length = (size_num * qty_per_item * item['qty']) / 1000.0
                except (ValueError, TypeError, AttributeError):
                    cut_length = 0
                
                row_key = (detail_name, size_str, str(qty_per_item), material)
                
                if row_key not in seen_rows:
                    seen_rows.add(row_key)
                    details_data.append([
                        Paragraph(detail_name, cell_style_left),
                        Paragraph(size_str, cell_style_center),
                        Paragraph(str(qty_per_item), cell_style_center),
                        Paragraph(str(qty_per_item * item['qty']), cell_style_center),
                        Paragraph(f"{cut_length:.2f}", cell_style_center),
                        Paragraph(material, cell_style_left)
                    ])
            
            if len(details_data) > 1:
                details_table = Table(details_data, colWidths=[25*mm, 18*mm, 16*mm, 20*mm, 20*mm, 33*mm])
                details_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                elements.append(details_table)
                elements.append(Spacer(1, 8))
        
        # === СПЕЦИФИКАЦИЯ НА ФУРНИТУРУ ===
        item_materials, item_furniture = get_materials_for_item(item['name'], item['articul'])
        if item_furniture:
            elements.append(Paragraph("<b>СПЕЦИФИКАЦИЯ НА ФУРНИТУРУ</b>", title_style))
            elements.append(Spacer(1, 3))
            
            furn_data = [[
                Paragraph('Наименование', cell_style_left),
                Paragraph('Кол-во на изд.', cell_style_center),
                Paragraph('Кол-во в заказе', cell_style_center)
            ]]
            
            for furn, furn_qty in item_furniture:
                if furn:
                    furn_data.append([
                        Paragraph(furn, cell_style_left),
                        Paragraph(str(furn_qty), cell_style_center),
                        Paragraph(str(furn_qty * item['qty']), cell_style_center)
                    ])
            
            if len(furn_data) > 1:
                furn_table = Table(furn_data, colWidths=[90*mm, 25*mm, 25*mm])
                furn_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT),
                    ('FONTSIZE', (0, 0), (-1, 0), 9),
                    ('FONTSIZE', (0, 1), (-1, -1), 8),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('TOPPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                elements.append(furn_table)
                elements.append(Spacer(1, 8))
        
        # === ОБЩИЙ МАТЕРИАЛ НА ПОЗИЦИЮ ===
        if details:
            materials_total = {}
            
            for detail in details:
                size = detail[1] if detail[1] else 0
                qty_per_item = detail[2] if detail[2] else 0
                material = (detail[3] or '').strip()
                
                if not material or qty_per_item <= 0:
                    continue
                
                try:
                    size_num = float(size) if size else 0
                    length = (size_num * qty_per_item * item['qty']) / 1000.0
                    
                    if material in materials_total:
                        materials_total[material] += length
                    else:
                        materials_total[material] = length
                except (ValueError, TypeError):
                    pass
            
            if materials_total:
                elements.append(Paragraph("_" * 100, normal_style))
                elements.append(Spacer(1, 4))
                elements.append(Paragraph("<b>ОБЩИЙ МАТЕРИАЛ НА ПОЗИЦИЮ</b>", title_style))
                elements.append(Spacer(1, 3))
                
                mat_data = [[
                    Paragraph('Материал', cell_style_left),
                    Paragraph('Количество', cell_style_center),
                    Paragraph('Ед. изм.', cell_style_center)
                ]]
                
                for material_name, total_length in materials_total.items():
                    length_str = str(int(total_length)) if total_length.is_integer() else f"{total_length:.2f}"
                    mat_data.append([
                        Paragraph(material_name, cell_style_left),
                        Paragraph(length_str, cell_style_center),
                        Paragraph('м', cell_style_center)
                    ])
                
                if len(mat_data) > 1:
                    mat_table = Table(mat_data, colWidths=[110*mm, 25*mm, 15*mm])
                    mat_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT),
                        ('FONTSIZE', (0, 0), (-1, 0), 9),
                        ('FONTSIZE', (0, 1), (-1, -1), 8),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('TOPPADDING', (0, 0), (-1, -1), 4),
                        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                    ]))
                    elements.append(mat_table)
        
        if idx < len(order_items):
            elements.append(PageBreak())
    
    # === ОБЩИЙ ОТЧЕТ ПО ЗАКАЗУ ===
    if include_summary and (materials or furniture):
        print("✅ ДОБАВЛЯЕМ ОБЩИЙ ОТЧЁТ")
        elements.append(PageBreak())
        elements.append(Paragraph(f"ОБЩИЙ ОТЧЕТ ПО ЗАКАЗУ № {order_number}", title_style))
        elements.append(Spacer(1, 10))
        
        # Отчет по материалам
        if materials:
            print(f"📊 Добавляем таблицу материалов ({len(materials)} позиций)")
            elements.append(Paragraph("<b>МАТЕРИАЛЫ (ОБЩИЕ НА ВЕСЬ ЗАКАЗ)</b>", header_style))
            elements.append(Spacer(1, 5))
            
            mat_data = [[
                Paragraph('№', cell_style_center),
                Paragraph('Материал', cell_style_left),
                Paragraph('Количество', cell_style_center),
                Paragraph('Ед. изм.', cell_style_center)
            ]]
            
            i = 1
            for material_name, total_qty in materials.items():
                qty_float = float(total_qty)
                qty_str = str(int(qty_float)) if qty_float.is_integer() else f"{qty_float:.2f}"
                mat_data.append([
                    Paragraph(str(i), cell_style_center),
                    Paragraph(material_name, cell_style_left),
                    Paragraph(qty_str, cell_style_center),
                    Paragraph('м', cell_style_center)
                ])
                i += 1
            
            if len(mat_data) > 1:
                mat_table = Table(mat_data, colWidths=[10*mm, 100*mm, 25*mm, 15*mm])
                mat_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                elements.append(mat_table)
                elements.append(Spacer(1, 15))
        
        # Отчет по фурнитуре
        if furniture:
            print(f"📊 Добавляем таблицу фурнитуры ({len(furniture)} позиций)")
            elements.append(Paragraph("<b>ФУРНИТУРА (ОБЩАЯ НА ВЕСЬ ЗАКАЗ)</b>", header_style))
            elements.append(Spacer(1, 5))
            
            furn_data = [[
                Paragraph('№', cell_style_center),
                Paragraph('Фурнитура', cell_style_left),
                Paragraph('Кол-во', cell_style_center),
                Paragraph('Ед. изм.', cell_style_center)
            ]]
            
            for i, (furn, qty) in enumerate(furniture.items(), 1):
                if furn:
                    furn_data.append([
                        Paragraph(str(i), cell_style_center),
                        Paragraph(furn, cell_style_left),
                        Paragraph(str(int(qty)), cell_style_center),
                        Paragraph('шт', cell_style_center)
                    ])
            
            if len(furn_data) > 1:
                furn_table = Table(furn_data, colWidths=[10*mm, 100*mm, 25*mm, 15*mm])
                furn_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('FONTNAME', (0, 0), (-1, -1), CYRILLIC_FONT),
                    ('FONTSIZE', (0, 0), (-1, 0), 10),
                    ('FONTSIZE', (0, 1), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
                ]))
                elements.append(furn_table)
        
        # === КАРТЫ РАСКРОЯ ===
        from config import load_config
        config = load_config()
        show_cutting = config.get('show_cutting_maps', False)
        
        if show_cutting:  # ← ПРОВЕРЯЕМ настройку из конфига
            print("✅ ДОБАВЛЯЕМ КАРТЫ РАСКРОЯ (настройка включена)")
            elements.append(PageBreak())
            elements.append(Paragraph(f"КАРТЫ РАСКРОЯ (хлыст {stock_length/1000:.1f}м)", title_style))
            elements.append(Spacer(1, 10))
            
            # Собираем детали по типам труб
            pipes = {}
            for item in order_items:
                details = get_item_details(item['name'], item['articul'])
                for detail in details:
                    material = (detail[3] or '').strip()
                    size = detail[1] if detail[1] else 0
                    qty_per_item = detail[2] if detail[2] else 0
                    
                    if not material or 'Труба' not in material:
                        continue
                    
                    size_str = str(size) if size else '0'
                    if 'x' in size_str.lower():
                        continue
                    
                    try:
                        length_mm = float(size)
                        if length_mm <= 0:
                            continue
                        
                        total_qty = qty_per_item * item['qty']
                        
                        if material not in pipes:
                            pipes[material] = []
                        pipes[material].append((length_mm, total_qty))
                    except:
                        pass
            
            # Для каждого типа трубы
            for pipe_type, parts in pipes.items():
                elements.append(Paragraph(f"<b>{pipe_type}</b>", header_style))
                elements.append(Spacer(1, 5))
                
                stock_length = config.get('cutting_stock_length', 6000)  # ← БЕРЁМ из конфига!
                blanks = optimize_cutting(parts, stock_length, kerf_width)
                
                for i, blank in enumerate(blanks, 1):
                    draw_pipe_blank(elements, blank, i, pipe_type, stock_length, kerf_width,
              cell_style_center, cell_style_left, CYRILLIC_FONT)
                
                elements.append(Spacer(1, 10))
        else:
            print("❌ Карты раскроя НЕ добавляются (настройка выключена)")
    else:
        if not include_summary:
            print("❌ Общий отчет НЕ добавляется (чекбокс выключен)")
        elif not materials and not furniture:
            print("❌ Нет данных для отчета")
    
    # ✅ ФУНКЦИИ ДЛЯ КОЛОНТИТУЛОВ
    def on_first_page(canvas, doc):
        canvas.saveState()
        canvas.setFont(CYRILLIC_FONT, 9)
        canvas.drawRightString(doc.pagesize[0] - 20*mm, doc.pagesize[1] - 15*mm, 
                              f"Заказ № {order_number}")
        canvas.drawRightString(doc.pagesize[0] - 20*mm, 15*mm, 
                              f"Лист 1 из {doc.page}")
        canvas.restoreState()
    
    def on_later_pages(canvas, doc):
        canvas.saveState()
        canvas.setFont(CYRILLIC_FONT, 9)
        canvas.drawRightString(doc.pagesize[0] - 20*mm, doc.pagesize[1] - 15*mm, 
                              f"Заказ № {order_number}")
        canvas.drawRightString(doc.pagesize[0] - 20*mm, 15*mm, 
                              f"Лист {doc.page} из {doc.page}")
        canvas.restoreState()
    
    try:
        doc.build(elements, onFirstPage=on_first_page, onLaterPages=on_later_pages)
        print(f"✅ PDF создан: {filepath}")
        return filepath
    except Exception as e:
        print(f"❌ Ошибка создания PDF: {e}")
        import traceback
        traceback.print_exc()
        return None

def print_order(filepath):
    """Отправляет PDF на печать"""
    try:
        os.startfile(filepath, "print")
        return True
    except Exception as e:
        print(f"Ошибка печати: {e}")
        return False

def add_cutting_maps(elements, order_items, stock_length,
                    title_style, header_style, cell_style_center,
                    cell_style_left, CYRILLIC_FONT):
    """Добавляет карты раскроя труб"""
    # ✅ ДОБАВЬ ЭТУ СТРОКУ В НАЧАЛО ФУНКЦИИ:
    from database import get_item_details
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib.colors import HexColor, lightgrey, black
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    from collections import defaultdict
    
    # Собираем все детали по типам труб
    pipes = defaultdict(list)  # {материал: [(длина_мм, количество_шт), ...]}
    
    for item in order_items:
        details = get_item_details(item['name'], item['articul'])  # ← Теперь работает!
        for detail in details:
            detail_name = (detail[0] or '').strip()
            size = detail[1] if detail[1] else 0
            qty_per_item = detail[2] if detail[2] else 0
            material = (detail[3] or '').strip()
            
            # Пропускаем если нет материала или это не труба
            if not material or 'Труба' not in material:
                continue
            
            # Пропускаем площадные материалы (с 'x' в размере)
            size_str = str(size) if size else '0'
            if 'x' in size_str.lower():
                continue
            
            try:
                length_mm = float(size)
                if length_mm <= 0:
                    continue
                
                # ✅ Общее количество деталей на всё изделие
                total_qty = qty_per_item * item['qty']
                
                if material not in pipes:
                    pipes[material] = []
                # ✅ Добавляем кортеж (длина, количество)
                pipes[material].append((length_mm, total_qty))
            except:
                continue
    
    if not pipes:
        return
    
    # Добавляем заголовок
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>КАРТЫ РАСКРОЯ (хлыст {stock_length/1000:.1f}м)</b>", header_style))
    elements.append(Spacer(1, 5))
    
    # Для каждого типа трубы
    for pipe_type, parts in pipes.items():
        elements.append(Paragraph(f"{pipe_type}", cell_style_left))
        elements.append(Spacer(1, 3))
        
        # ✅ Оптимизируем раскрой с учётом длины хлыста из конфига
        blanks = optimize_cutting(parts, stock_length)
        
        # Рисуем карты раскроя
        for i, blank in enumerate(blanks, 1):
            draw_pipe_blank(elements, blank, i, pipe_type, stock_length,
                          cell_style_center, cell_style_left, CYRILLIC_FONT)
        
        elements.append(Spacer(1, 5))

def optimize_cutting(details_list, stock_length=6000, kerf_width=3):
    """
    Оптимизирует раскрой деталей на хлысты с учётом толщины реза
    
    Args:
        details_list: список кортежей [(длина_мм, количество_шт), ...]
        stock_length: длина хлыста в мм (из конфига)
        kerf_width: толщина реза в мм (из конфига, по умолчанию 3мм)
    
    Returns:
        список хлыстов, каждый хлыст - список кортежей (длина, позиция)
    """
    # ✅ РАСПАКОВЫВАЕМ кортежи (длина, количество) в отдельные детали
    all_parts = []
    for length, qty in details_list:
        for _ in range(int(qty)):
            all_parts.append(float(length))
    
    # Сортируем по убыванию длины (для лучшего заполнения)
    all_parts.sort(reverse=True)
    
    blanks = []
    remaining = all_parts.copy()
    
    while remaining:
        # Первый Fit Decreasing алгоритм с учётом толщины реза
        blank = []
        current_length = 0
        
        for length in remaining[:]:
            # ✅ УЧИТЫВАЕМ ТОЛЩИНУ РЕЗА:
            # - Если это первая деталь на хлысте: занимаемое место = длина детали
            # - Если это не первая деталь: занимаемое место = длина детали + толщина реза
            needed_space = length
            if blank:  # Если это не первая деталь
                needed_space += kerf_width
            
            if current_length + needed_space <= stock_length:
                blank.append((length, current_length))
                current_length += needed_space  # ✅ Добавляем с учётом реза
                remaining.remove(length)
        
        blanks.append(blank)
    
    return blanks
    
def draw_pipe_blank(elements, blank, blank_num, pipe_type, stock_length, kerf_width,
                   cell_style_center, cell_style_left, CYRILLIC_FONT):
    """Рисует один хлыст с раскладкой"""
    from reportlab.graphics.shapes import Drawing, Rect, String
    from reportlab.lib.colors import HexColor, lightgrey, black
    from reportlab.platypus import Table, TableStyle, Paragraph, Spacer
    
    # Считаем общую длину с учётом пропилов
    total_length = sum(b[0] for b in blank)
    total_kerf = kerf_width * (len(blank) - 1) if len(blank) > 1 else 0
    used_length = total_length + total_kerf
    waste = stock_length - used_length
    fill_percent = (used_length / stock_length) * 100
    
    # ✅ ВСЁ В ОДНОЙ СТРОКЕ (не 3 столбца!)
    table_data = [[
        Paragraph(f"Хлыст #{blank_num} | Заполнение: {fill_percent:.1f}% | Отход: {waste}мм", 
                 cell_style_center)
    ]]
    
    # ✅ ГРАФИЧЕСКОЕ ПРЕДСТАВЛЕНИЕ
    drawing = Drawing(width=500, height=50)
    
    # Рисуем хлыст
    x_start = 0
    # ✅ ЧЕРЕДОВАНИЕ: БЕЛЫЙ - СВЕТЛО-СЕРЫЙ - БЕЛЫЙ
    gray_colors = ['#FFFFFF', '#E8E8E8', '#FFFFFF', '#E8E8E8', '#FFFFFF']
    
    for i, (length, pos) in enumerate(blank):
        width = (length / stock_length) * 500  # Масштабируем
        # ✅ Чередование цветов
        color = gray_colors[i % 2]  # ← Только 2 цвета!
        
        # Прямоугольник детали
        drawing.add(Rect(x_start, 5, width, 40,
                        fillColor=HexColor(color),
                        strokeColor=black,
                        strokeWidth=0.5))
        
        # ✅ ТЕКСТ С ДЛИНОЙ — ПО ЦЕНТРУ ПРЯМОУГОЛЬНИКА
        text = f"{int(length)}"
        drawing.add(String(x_start + width/2, 23,  # 23 = середина по высоте
                         text,
                         textAnchor="middle",
                         fontSize=8,
                         fillColor=black))
        
        x_start += width
        
        # ✅ РИСУЕМ ПРОПИЛ (если это не последняя деталь)
        if i < len(blank) - 1 and kerf_width > 0:
            kerf_px = (kerf_width / stock_length) * 500
            if kerf_px >= 1:
                from reportlab.graphics.shapes import Line
                drawing.add(Line(x_start, 0, x_start, 50,
                               strokeColor=black,
                               strokeWidth=0.5,
                               dashArray=[2, 2]))
                x_start += kerf_px
    
    # Остаток (пунктирный)
    if waste > 0:
        waste_width = (waste / stock_length) * 500
        drawing.add(Rect(x_start, 5, waste_width, 40,
                        fillColor=lightgrey,
                        strokeColor=black,
                        strokeWidth=0.5,
                        dashArray=[3, 3]))
        if waste_width > 30:
            drawing.add(String(x_start + waste_width/2, 23,
                             f"✂{int(waste)}",
                             textAnchor="middle",
                             fontSize=7,
                             fillColor=black))
    
    # Общая рамка
    drawing.add(Rect(0, 0, 500, 50,
                    fillColor=None,
                    strokeColor=black,
                    strokeWidth=1))
    
    table_data.append([drawing])
    
    # ✅ ТАБЛИЦА С ОДНОЙ КОЛОНКОЙ (на всю ширину)
    pipe_table = Table(table_data, colWidths=[500])
    pipe_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, black),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),  # ← ВСЁ ПО ЦЕНТРУ!
        ('FONTNAME', (0, 0), (-1, 0), CYRILLIC_FONT),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
    ]))
    
    elements.append(pipe_table)
    elements.append(Spacer(1, 5))