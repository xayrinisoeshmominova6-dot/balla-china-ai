# BALLA CHINA AI MANAGER

O'zbek tilli o'quvchilarga Xitoy tilini o'rgatuvchi **Balla China** brendi uchun AI yordamida Instagram kontent tayyorlash tizimi.

> **Asosiy qoida:** tizim kontentni faqat **tayyorlaydi**. Instagram'ga hech narsa sizning Telegram orqali aniq tasdig'ingizsiz joylanmaydi.

---

## Hozirgi holat: 2-bosqich ✅

| Bosqich | Mazmuni | Holat |
|---|---|---|
| 0 | Loyiha tuzilmasi va sozlamalar | ✅ Tayyor |
| 1 | Birinchi kontent (terminalda) | ✅ Tayyor |
| 2 | Telegram orqali tasdiqlash, Carousel, Reels | ✅ Tayyor |
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
playwright install chromium
```
Ikkinchi buyruq dizayn uchun brauzerni yuklaydi (bir marta, ~150 MB).

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

Reels ssenariysi uchun: `python main.py "salomlashish" --hsk 1 --format reels`

### 7. Telegram botni ulash
1. Telegram'da **@BotFather** ga yozing → `/newbot` → nom bering → **token** oling.
2. Telegram'da **@userinfobot** ga yozing → u sizning **ID** raqamingizni beradi.
3. `.env` fayliga yozing:
   ```
   TELEGRAM_BOT_TOKEN=<BotFather bergan token>
   TELEGRAM_ADMIN_CHAT_ID=<sizning ID raqamingiz>
   ```
4. Botni ishga tushiring:
   ```bash
   python main.py --bot
   ```
5. Telegram'da botingizga `/start` yozing.

Bot faqat **sizning** ID'ingizga javob beradi. Boshqa odamlar yozsa — javob bermaydi.

**Bot buyruqlari:**

| Buyruq | Nima qiladi |
|---|---|
| `/new salomlashish 1` | Carousel qoralama (oxirgi raqam — HSK, ixtiyoriy) |
| `/reels salomlashish 2` | Reels ssenariysi |
| `/list` | Oxirgi 10 ta qoralama va holati |
| `/show 3` | 3-qoralamani qayta ko'rish |
| `/cancel` | Tahrirni bekor qilish |

**Tugmalar:** ✅ Tasdiqlash → "Ha, aniq tasdiqlayman" (ikki bosqich) · ✏️ Tahrir (izoh yozasiz, qayta tayyorlanadi) · ❌ Rad etish.

> 2-bosqichda tasdiqlash faqat holatni "tasdiqlangan" qiladi. **Instagram'ga joylash 3-bosqichda** qo'shiladi.

### 8. Dizayn
Slaydlar HTML/CSS shablondan brauzer orqali PNG qilib chiziladi:
- Shablon: `design/templates/slide.html.j2` (CSS shu faylning boshida)
- Ranglar va Instagram nomi: `config/brand.yaml`
- Shriftlar: Montserrat, Noto Sans SC, Noto Serif SC (Google Fonts, internet orqali yuklanadi)

**Carousel tuzilmasi (10 slayd, 1080×1350):**

| Slayd | Mazmuni |
|---|---|
| 1. Muqova | Kuchli sarlavha (urg'u oltin rangda), so'zlar ko'rinishi, "Varaqlang" |
| 2–7. So'zlar | 田字格 katakda ieroglif, **ton ranglari** bo'yicha pinyin, tarjima, 🧠 eslab qolish usuli, misol gap |
| 8. Keng tarqalgan xato | ✕ Xato / ✓ To'g'ri + izoh |
| 9. Test | Savol + A/B/C — izohlarda faollikni oshiradi |
| 10. Takrorlash | Barcha so'zlar, maslahat, Saqlang / Ulashing / Obuna bo'ling |

**Reels:** sahnama-sahna ssenariy + 1080×1920 muqova rasmi.

Ton ranglari: 1-ton qizil, 2-ton yashil, 3-ton ko'k, 4-ton binafsha, neytral kulrang.

### 9. Testlar (API kalitsiz ishlaydi)
```bash
python -m unittest discover tests
```

---

## Qanday ishlaydi

```
Telegram: /new mavzu 2
      │
      ▼
📚 Education → (🎬 Reels ssenariy) → ✍️ Caption → 🔍 Quality Control
                                                     │ xato bo'lsa — 1 marta qayta yoziladi
                                                     ▼
                                     🎨 Carousel slaydlari (1080×1350 PNG)
                                                     │
                                                     ▼
                        Telegram: rasmlar + mazmun + caption + [✅] [✏️] [❌]
                                                     │
                              ✅ → "Ha, aniq" → holat: tasdiqlangan
```

**Holatlar** (`storage/database.py`): `qc_passed/qc_failed → awaiting_approval → approved → published`.
Tasdiqlanmagan qoralamani "published" qilish kod darajasida **taqiqlangan**.

- **Education agent** (`agents/education.py`): 4–6 ta so'z, tonli pinyin, o'zbekcha tarjima, misol gap.
- **Caption agent** (`agents/caption.py`): hook, matn, CTA, heshteglar.
- **Quality Control** (`agents/quality.py`): avval Python qoidalari (kirill harflari, uzunlik, heshteglar), keyin Claude pinyin/ton/tarjimani tekshiradi.
- **Reels agent** (`agents/reels.py`): sahnama-sahna ssenariy (videoni o'zingiz suratga olasiz).
- **Carousel agent** (`agents/carousel.py`): HTML shablondan professional slaydlar chizadi (Claude'siz, bepul).
- **Manager** (`agents/manager.py`): hammasini ketma-ket boshqaradi.
- **Telegram bot** (`integrations/telegram_bot.py`): ko'rsatadi va tasdig'ingizni oladi.

Slayd ranglari va Instagram nomi: `config/brand.yaml` → `colors`, `instagram_handle`.

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
