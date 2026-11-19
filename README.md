# BALLA CHINA AI MANAGER

O'zbek tilli o'quvchilarga Xitoy tilini o'rgatuvchi **Balla China** brendi uchun AI yordamida Instagram kontent tayyorlash tizimi.

> **Asosiy qoida:** tizim kontentni faqat **tayyorlaydi**. Instagram'ga hech narsa sizning Telegram orqali aniq tasdig'ingizsiz joylanmaydi.

---

## Hozirgi holat: 1-bosqich ✅

| Bosqich | Mazmuni | Holat |
|---|---|---|
| 0 | Loyiha tuzilmasi va sozlamalar | ✅ Tayyor |
| 1 | Birinchi kontent (terminalda) | ✅ Tayyor |
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
Keyin `.env` faylini oching va `ANTHROPIC_API_KEY=` dan keyin Claude API kalitingizni yozing
(olish joyi: https://console.anthropic.com → API Keys). Boshqa kalitlar hozircha shart emas.

### 5. Sozlamalarni tekshiring
```bash
python main.py --check
```
`ANTHROPIC_API_KEY` yonida ✅ chiqsa — tayyor.

### 6. Birinchi kontentni yarating
```bash
python main.py "salomlashish" --hsk 1
python main.py "restoranda buyurtma berish" --hsk 3
```
Natija:
- ekranda: so'zlar (ieroglif, pinyin, tarjima, misol), caption va sifat nazorati hisoboti;
- faylda: `output/` papkasida JSON ko'rinishida.

**Hech narsa Instagram'ga joylanmaydi** — bu faqat qoralama.

### 7. Testlar (API kalitsiz ishlaydi)
```bash
python -m unittest discover tests
```

---

## Qanday ishlaydi (1-bosqich)

```
Mavzu + HSK  →  📚 Education agent  →  ✍️ Caption agent  →  🔍 Quality Control
                                                                │
                                       xato bo'lsa ◄────────────┘
                                       1 marta qayta yoziladi
                                                                │
                                                                ▼
                                                   output/…json (qoralama)
```

- **Education agent** (`agents/education.py`): 4–6 ta so'z, tonli pinyin, o'zbekcha tarjima, misol gap.
- **Caption agent** (`agents/caption.py`): hook, matn, CTA, heshteglar.
- **Quality Control** (`agents/quality.py`): avval Python qoidalari (kirill harflari, uzunlik, heshteglar), keyin Claude pinyin/ton/tarjimani tekshiradi.
- **Manager** (`agents/manager.py`): hammasini ketma-ket boshqaradi.

**Agentlar ko'rsatmalarini o'zgartirish:** `prompts/` papkasidagi `.md` fayllarni oddiy matn sifatida tahrirlang — kodga tegish shart emas.

> ⚠️ Claude ba'zan pinyin yoki tonda xato qilishi mumkin. QC ko'p xatolarni ushlaydi, lekin yakuniy tekshiruv — sizda.

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
