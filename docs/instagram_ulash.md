# Instagram'ni ulash — qadamma-qadam qo'llanma

Bu qo'llanma **Balla China Language** Instagram akkauntini tizimga ulashni tushuntiradi.

> ⏱ Taxminan 30–40 daqiqa vaqt oladi.
> 🔐 Token — bu akkauntingizga kirish kaliti. Uni hech kimga, hatto chatga ham yubormang.

> ℹ️ Meta (Facebook) saytining tuzilishi vaqti-vaqti bilan o'zgaradi. Tugma nomlari
> bu yerda yozilganidan biroz farq qilishi mumkin. Adashib qolsangiz, ekran
> rasmini oling, lekin **token ko'rinmasin**.

---

## 1-qadam. Akkaunt turini tekshirish

API faqat **Professional** akkauntlarda (Business yoki Creator) ishlaydi.

1. Instagram ilovasida profilingizga o'ting → ☰ menyu → **Settings and privacy**.
2. **Account type and tools** bo'limini oching.
3. Agar "Switch to professional account" yozuvi ko'rinsa, akkaunt hali oddiy. Bu tugmani bosing va **Business** turini tanlang.

## 2-qadam. Meta Developer akkaunti

1. https://developers.facebook.com saytini oching va Facebook akkauntingiz bilan kiring.
2. Agar birinchi marta kirayotgan bo'lsangiz, developer sifatida ro'yxatdan o'ting.

## 3-qadam. Ilova (App) yaratish

1. **My Apps** → **Create App** tugmasini bosing.
2. Ilovaga nom bering, masalan `Balla China AI`.
3. Foydalanish maqsadi (use case) so'ralganda Instagram bilan bog'liq variantni tanlang. U odatda **"Manage messaging & content on Instagram"** deb nomlanadi.
4. Ilova yaratiladi.

## 4-qadam. Instagram akkauntini ulash va token olish

1. Ilova sahifasida **Instagram** → **API setup with Instagram login** bo'limini oching.
2. **Generate access tokens** qismida **Add account** tugmasini bosing va `Balla China Language` akkauntiga kiring.
3. Ruxsatlarni bering. Kerakli ruxsatlar:
   - `instagram_business_basic` — akkaunt ma'lumotlarini o'qish
   - `instagram_business_content_publish` — post joylash (keyinroq kerak bo'ladi)
   - `instagram_business_manage_insights` — statistika (analitika uchun)
4. Akkaunt yonida **Generate token** tugmasini bosing va tokenni nusxalang.
5. Akkaunt yonida ko'rsatilgan **ID** raqamini ham nusxalang.

## 5-qadam. `.env` fayliga yozish

Loyiha papkasidagi `.env` faylini oching va quyidagilarni to'ldiring:

```
INSTAGRAM_ACCESS_TOKEN=bu_yerga_token
INSTAGRAM_BUSINESS_ACCOUNT_ID=bu_yerga_ID
INSTAGRAM_API_HOST=graph.instagram.com
```

Faylni saqlang.

## 6-qadam. Tekshirish

Terminalda quyidagini yozing:

```bash
balla instagram
```

Ulanish ishlasa, shunday natija chiqadi:

```
✅ Instagram'ga ulanish ishlayapti!

  Akkaunt:      @...
  Obunachilar:  ...
```

Xato chiqsa, xabar sababini o'zbekcha tushuntiradi. Masalan: "Token muddati o'tgan".

---

## Muhim eslatmalar

- **Token muddati.** Token cheksiz amal qilmaydi. Muddati tugaganda yangi token olish kerak bo'ladi. Keyingi bosqichlarda tokenni avtomatik yangilashni qo'shamiz.
- **Token oshkor bo'lsa.** Instagram'da parolni o'zgartiring va Meta Developer sahifasida yangi token oling. Shunda eski token ishlamay qoladi.
- **Hozirgi imkoniyat.** `balla instagram` buyrug'i faqat ma'lumot **o'qiydi**. Post joylash keyingi bosqichlarda qo'shiladi va faqat siz **tasdiqlagan** postlar uchun ishlaydi.
- **Facebook sahifa orqali ulash.** Akkauntingiz Facebook sahifasi orqali ulangan bo'lsa (eski usul), `.env` faylida `INSTAGRAM_API_HOST=graph.facebook.com` deb yozing.
