#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт объединяет все .py файлы из корневой папки в один txt файл.
Подпапки НЕ учитываются.
Использование: python combine_py.py
"""

import os
from datetime import datetime

# Настройки
OUTPUT_FILE = "Исходник.txt"  # Имя выходного файла
TARGET_FOLDER = "."  # Текущая папка (корень)

def get_py_files_root_only(folder):
    """Находит все .py файлы ТОЛЬКО в корневой папке (без подпапок)"""
    py_files = []
    
    # listdir возвращает только файлы в указанной папке (не рекурсивно)
    for file in os.listdir(folder):
        full_path = os.path.join(folder, file)
        
        # Проверяем, что это файл (не папка) и заканчивается на .py
        if os.path.isfile(full_path) and file.endswith(".py"):
            # Исключаем сам скрипт combine_py.py
            if file != "combine_py.py":
                py_files.append(file)
    
    # Сортируем по имени
    py_files.sort()
    return py_files

def combine_files(py_files, output_file):
    """Объединяет содержимое файлов в один txt"""
    with open(output_file, "w", encoding="utf-8") as outfile:
        # Заголовок
        outfile.write("=" * 80 + "\n")
        outfile.write("ИСХОДНЫЙ КОД ПРОЕКТА «ЗАКАЗ МК»\n")
        outfile.write(f"Дата создания: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}\n")
        outfile.write(f"Всего файлов: {len(py_files)}\n")
        outfile.write("=" * 80 + "\n\n")
        
        # Содержимое каждого файла
        for i, py_file in enumerate(py_files, 1):
            outfile.write("\n" + "=" * 80 + "\n")
            outfile.write(f"📄 ФАЙЛ: {py_file}\n")
            outfile.write(f"#{i} из {len(py_files)}\n")
            outfile.write("=" * 80 + "\n\n")
            
            try:
                with open(py_file, "r", encoding="utf-8") as infile:
                    content = infile.read()
                    outfile.write(content)
                    if not content.endswith("\n"):
                        outfile.write("\n")
            except Exception as e:
                outfile.write(f"⚠️ Ошибка чтения файла: {e}\n")
            
            outfile.write("\n")
    
    return output_file

def main():
    print("=" * 60)
    print("🔧 Объединение .py файлов в Исходник.txt")
    print("=" * 60)
    
    # Находим все .py файлы ТОЛЬКО в корне
    py_files = get_py_files_root_only(TARGET_FOLDER)
    
    if not py_files:
        print("❌ .py файлы в корневой папке не найдены!")
        return
    
    print(f"✅ Найдено файлов: {len(py_files)}")
    for f in py_files:
        print(f"   • {f}")
    
    # Объединяем
    output_file = combine_files(py_files, OUTPUT_FILE)
    
    # Размер файла
    file_size = os.path.getsize(output_file)
    if file_size > 1024 * 1024:
        size_str = f"{file_size / (1024 * 1024):.2f} МБ"
    else:
        size_str = f"{file_size / 1024:.2f} КБ"
    
    print("\n" + "=" * 60)
    print(f"✅ Готово!")
    print(f"📁 Выходной файл: {output_file}")
    print(f"📊 Размер: {size_str}")
    print("=" * 60)

if __name__ == "__main__":
    main()