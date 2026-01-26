import os
from PIL import Image, ImageDraw, ImageFont
from pathlib import Path

def create_receipt(text_lines, filename, folder="inbox", blur=False):
    Path(folder).mkdir(exist_ok=True)
    
    # Белый фон, размер как у чека
    img = Image.new('RGB', (400, 600), color='white')
    d = ImageDraw.Draw(img)
    
    # Пытаемся загрузить шрифт, иначе дефолтный
    try:
        font = ImageFont.truetype("arial.ttf", 20)
    except IOError:
        font = ImageFont.load_default()

    y = 50
    for line in text_lines:
        d.text((20, y), line, fill='black', font=font)
        y += 30
    
    # Сохраняем
    path = os.path.join(folder, filename)
    img.save(path)
    print(f"Created: {path}")

def generate():
    # 1. Хороший чек (Starbucks)
    create_receipt([
        "STARBUCKS COFFEE",
        "123 Main St, New York",
        "----------------",
        "Date: 2026-01-15",
        "Time: 08:30 AM",
        "----------------",
        "Latte Grande   $ 5.50",
        "Muffin         $ 3.00",
        "----------------",
        "TOTAL          $ 8.50",
        "Payment: Visa **** 1234"
    ], "receipt_starbucks.jpg")

    # 2. Инвойс (AWS)
    create_receipt([
        "AMAZON WEB SERVICES",
        "Invoice #INV-2026001",
        "Date: 2026-02-01",
        "Bill to: John Doe",
        "----------------",
        "Service: EC2 Instance",
        "Region: us-east-1",
        "----------------",
        "TOTAL DUE:     $ 45.00",
        "Currency: USD"
    ], "invoice_aws.png")

    # 3. "Плохой" чек (без даты, чтобы ИИ засомневался)
    create_receipt([
        "LOCAL MARKET",
        "Date: ??/??/2026", # Нечитаемая дата
        "Milk           12000 UZS",
        "Bread          4000 UZS",
        "TOTAL          16000 UZS"
    ], "bad_receipt.jpg")

if __name__ == "__main__":
    generate()