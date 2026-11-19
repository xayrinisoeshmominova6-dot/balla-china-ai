# Balla China AI — Instagram menejeri

**Balla China Language** Instagram sahifasi uchun kontent tayyorlaydigan AI tizimi.
Auditoriya: xitoy tilini o'rganayotgan o'zbek tilli foydalanuvchilar.

## Holat

| Bosqich | Mazmuni | Holati |
|---|---|---|
| 1 | Asos: sozlamalar, Claude ulanishi, sxemalar, ma'lumotlar bazasi | ✅ tayyor |
| 2 | Xitoy tili o'qituvchisi + tekshiruv qavati | ⏳ |
| 3 | Karusel, Reels, Caption, Kreativ direktor | ⏳ |
| 4 | Kontent strategi (kalendar) | ⏳ |
| 5 | Tasdiqlash + Publisher (quruq rejim) | ⏳ |
| 6 | FastAPI + n8n | ⏳ |
| 7 | Instagram API + Analitika | ⏳ |

## O'rnatish (qadamma-qadam)

```bash
# 1. Virtual muhit yaratish (loyiha kutubxonalari uchun alohida "quti")
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

# 2. Loyihani o'rnatish
pip install -e ".[dev]"

# 3. Sozlamalar faylini yaratish
cp .env.example .env
# Endi .env faylini oching va ANTHROPIC_API_KEY= dan keyin kalitingizni yozing

# 4. Tekshirish
balla check
pytest
```

## 🔐 Xavfsizlik qoidalari

- API kalitlari **faqat** `.env` faylida turadi. `.env` GitHub'ga yuklanmaydi.
- Kalitni hech qachon chatga, kodga yoki skrinshotga qo'ymang.
- Kalit tasodifan oshkor bo'lsa, uni darhol https://console.anthropic.com da o'chirib, yangisini yarating.

## ✅ Tasdiqlash qoidasi

Post faqat shu yo'l bilan joylanadi:

```
qoralama → tekshiruvda → tasdiqlangan → joylangan
```

Tasdiqlanmagan postni joylab bo'lmaydi. Bu qoida kodda yozilgan va testlar bilan tekshiriladi.

## 🇨🇳 Xitoycha ma'lumotlar aniqligi

- AI ishonchi komil bo'lmagan ma'lumotni `uncertain` deb belgilaydi.
- Pinyin `pypinyin` yordamida avtomatik tekshiriladi (2-bosqich).
- Har bir so'z o'qituvchi tasdiqlamaguncha `teacher_verified = false` holatida qoladi.

## Tuzilma

```
src/balla/
  config.py            sozlamalar (.env'dan)
  llm/claude_client.py Claude API bilan bog'lanish
  schemas/             ma'lumot shakllari (dars, holatlar)
  storage/database.py  SQLite + tasdiqlash qoidalari
  prompts/             AI ko'rsatmalari (.md fayllar)
  agents/              AI agentlar
  cli.py               `balla` buyrug'i
tests/                 avtomatik testlar
```
