# BALLA CHINA AI MANAGER

O'zbek tilli o'quvchilarga Xitoy tilini o'rgatuvchi **Balla China** brendi uchun AI yordamida Instagram kontent tayyorlash tizimi.

> **Asosiy qoida:** tizim kontentni faqat **tayyorlaydi**. Instagram'ga hech narsa sizning Telegram orqali aniq tasdig'ingizsiz joylanmaydi.

---

## Hozirgi holat: 0-bosqich ✅

| Bosqich | Mazmuni | Holat |
|---|---|---|
| 0 | Loyiha tuzilmasi va sozlamalar | ✅ Tayyor |
| 1 | Birinchi kontent (terminalda) | ⏳ |
| 2 | Telegram orqali tasdiqlash | ⏳ |
| 3 | Instagram'ga joylash | ⏳ |
| 4 | Strategiya, analitika, n8n | ⏳ |

---

## O'rnatish (qadamma-qadam)

### 1. Python o'rnating
Python **3.10** yoki undan yangi versiyasi kerak. Tekshirish:
```bash
python --version
```

### 2. Virtual muhit yarating (tavsiya etiladi)
```bash
python -m venv .venv
# Mac/Linux:
source .venv/bin/activate
# Windows:
.venv\Scripts\activate
```

### 3. Kutubxonalarni o'rnating
```bash
pip install -r requirements.txt
```

### 4. `.env` faylini yarating
```bash
cp .env.example .env
```
Keyin `.env` faylini oching va kalitlarni yozing. **0-bosqichda kalit shart emas** — bo'sh qoldirsangiz ham bo'ladi.

### 5. Ishga tushiring
```bash
python main.py
```
Ekranda brend sozlamalari va kalitlar holati chiqsa — hammasi to'g'ri ✅

---

## 🔐 Xavfsizlik qoidalari

1. **Kalitlar faqat `.env` faylida.** Bu fayl `.gitignore` orqali GitHub'dan himoyalangan.
2. **`.env` faylini hech kimga yubormang** — chatga ham, Telegram'ga ham.
3. Kalit tasodifan oshkor bo'lsa — darhol uni tegishli saytda **o'chirib, yangisini oling**.
4. `DRY_RUN=true` turganda Instagram'ga hech narsa yuborilmaydi.
5. Telegram bot faqat `TELEGRAM_ADMIN_CHAT_ID` dagi odamga (sizga) javob beradi.

---

## Papkalar tuzilmasi

```
config/         Sozlamalar (settings.py) va brend (brand.yaml)
agents/         AI agentlar — har biri alohida fayl (1-bosqichdan)
prompts/        Agentlar uchun ko'rsatmalar (oddiy matn)
integrations/   Telegram bot va Instagram ulanishi
storage/        Ma'lumotlar bazasi (SQLite)
design/         Shriftlar va carousel shablonlari
output/         Yaratilgan rasmlar (GitHub'ga yuklanmaydi)
data/           Baza fayli (GitHub'ga yuklanmaydi)
n8n/            n8n workflow'lari (4-bosqich)
tests/          Testlar
main.py         Ishga tushirish nuqtasi
```

## Brend sozlamalari

`config/brand.yaml` faylida: lotin yozuvi, aralash HSK darajalari (1–6), ranglar, heshteglar, ohang. Bu faylni kodga tegmasdan tahrirlashingiz mumkin.
