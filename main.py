"""BALLA CHINA AI MANAGER — ishga tushirish nuqtasi.

0-bosqich: loyiha to'g'ri o'rnatilganini tekshiradi.
Ishga tushirish:  python main.py
"""
from config import settings


def main() -> None:
    print("=== BALLA CHINA AI MANAGER ===\n")

    brand = settings.load_brand()
    print(f"Brend: {brand['brand']['name']}")
    print(f"Yozuv: {brand['audience']['script']}")
    print(f"HSK darajalari: {brand['content']['hsk_levels']}\n")

    print(".env fayli:", "topildi" if settings.ENV_FILE.exists() else "YO'Q (README'ga qarang)")
    print("Kalitlar holati (qiymatlar ko'rsatilmaydi):")
    for name, is_set in settings.key_status().items():
        print(f"  {'✅' if is_set else '⬜'} {name}")

    mode = "YOQIQ — Instagram'ga hech narsa yuborilmaydi" if settings.DRY_RUN else "O'CHIQ"
    print(f"\nSinov rejimi (DRY_RUN): {mode}")
    print("\n0-bosqich tayyor. ✅")


if __name__ == "__main__":
    main()
