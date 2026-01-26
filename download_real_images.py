import io
import zipfile
import urllib.request
import os
import ssl
from pathlib import Path

# --- FIX: Отключаем проверку SSL (для macOS) ---
ssl._create_default_https_context = ssl._create_unverified_context

# Используем другое, надежное зеркало датасета (где файлы лежат не в LFS)
URL = "https://github.com/zzzDavid/ICDAR-2019-SROIE/archive/refs/heads/master.zip"
TARGET_DIR = Path("./sroie_test/inbox")

print(f"Downloading repo archive from {URL}...")
print("This might take 1-2 minutes (approx 280MB)...")

try:
    # Скачиваем архив в память
    with urllib.request.urlopen(URL) as resp:
        # Читаем весь архив сразу
        archive_data = resp.read()
        archive = zipfile.ZipFile(io.BytesIO(archive_data))
    
    # Создаем папку, если нет
    if TARGET_DIR.exists():
        # Чистим старые "битые" файлы
        for f in TARGET_DIR.glob("*"):
            f.unlink()
    TARGET_DIR.mkdir(parents=True, exist_ok=True)
    
    count = 0
    print("Extracting images...")
    
    # Ищем картинки внутри архива (где бы они ни лежали)
    for file in archive.namelist():
        # Игнорируем системные папки macOS и берем только jpg
        if file.lower().endswith(".jpg") and "__MACOSX" not in file:
            
            # Читаем файл
            img_data = archive.read(file)
            
            # Простая проверка: настоящий файл не может весить 130 байт (это LFS-ссылка)
            if len(img_data) < 1000:
                continue
                
            filename = Path(file).name
            
            # Сохраняем
            with open(TARGET_DIR / filename, "wb") as f:
                f.write(img_data)
                
            print(f" Saved: {filename} ({len(img_data)//1024} KB)")
            count += 1
            if count >= 10: # Нам хватит 30 штук
                break
                
    if count == 0:
        print("\nWARNING: No images found! Check the repository structure.")
    else:
        print(f"\nSuccess! Saved {count} real images to {TARGET_DIR}")

except Exception as e:
    print(f"\nError: {e}")