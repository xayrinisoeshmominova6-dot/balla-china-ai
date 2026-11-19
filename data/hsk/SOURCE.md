# HSK so'zlar ro'yxati — manba

> ⚠️ **HOLAT: o'qituvchi tomonidan hali TEKSHIRILMAGAN.**
> Bu ro'yxat ochiq manbadan avtomatik import qilingan. Darslar ishlatilishidan
> oldin o'qituvchi uni (hech bo'lmaganda ishlatiladigan so'zlarni) ko'rib chiqishi kerak.

## Fayllar

| Fayl | Mazmuni |
|---|---|
| `hsk3_level1.json` | Yangi HSK (3.0) 1-daraja so'zlari |
| `hsk3_level2.json` | Yangi HSK (3.0) 2-daraja (faqat yangi so'zlar) |
| `hsk3_level3.json` | Yangi HSK (3.0) 3-daraja (faqat yangi so'zlar) |

Har bir yozuv: `hanzi`, `pinyin` (lug'atdagi asl ohang bilan), `meanings_en`, `pos`, `level`.

## Manba va litsenziya

- Ma'lumotlar to'plami: [drkameleon/complete-hsk-vocabulary](https://github.com/drkameleon/complete-hsk-vocabulary) — MIT litsenziyasi.
- Undagi HSK 3.0 ro'yxatlari manbasi: [elkmovie/hsk30](https://github.com/elkmovie/hsk30).
- Inglizcha ta'riflar: [CC-CEDICT](https://www.mdbg.net/chinese/dictionary?page=cc-cedict) — CC BY-SA 4.0.

## Bilinishi kerak bo'lgan cheklovlar

- So'zlar soni rasmiy HSK 3.0 standartidagi sonlardan biroz farq qilishi mumkin,
  chunki manbada ba'zi yozuvlar birlashtirilgan yoki ajratilgan.
- Pinyin lug'at shaklida (asl ohang). Gapdagi ohang o'zgarishlari (masalan 不, 一) ko'rsatilmagan.
- Inglizcha ta'riflar umumiy lug'atdan olingan, faqat HSK uchun moslashtirilmagan.

## Yangilash

```bash
python scripts/import_hsk.py YUKLANGAN_PAPKA
```
