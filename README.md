# KASSA.UZ — birinchi ishlaydigan lokal MVP (v0.1)

Texnik topshiriqdagi **asosiy savdo zanjiri** uchun kod: login, kompaniya va filial ajratilishi, mahsulot/SKU/barcode, kirim, ombor qoldig‘i, POS, naqd/karta to‘lovni *qayd etish*, kassa smenasi, hisobot, CSV eksport, audit. Frontend responsiv, USB/Bluetooth klaviatura-emulyatsiyali skaner bilan barcode maydonida ishlaydi.

## Ishga tushirish

Python 3.10+ o‘rnating. Terminalda shu papkaga kiring:

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# macOS/Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

Admin parolini (12+ belgi) o‘zingiz belgilang:

Windows PowerShell:
```powershell
$env:KASSA_ADMIN_PASSWORD="SizningKuchliParolingiz123!"
python app.py seed
uvicorn app:app --host 127.0.0.1 --port 8000
```

macOS/Linux:
```bash
export KASSA_ADMIN_PASSWORD='SizningKuchliParolingiz123!'
python app.py seed
uvicorn app:app --host 127.0.0.1 --port 8000
```

Brauzer: **http://127.0.0.1:8000**. Login: `owner`, parol: yuqorida belgilaganingiz. API hujjatlari: `http://127.0.0.1:8000/docs`.

Demo katalogga uchta mahsulot yoziladi, **qoldiq 0**. Sinash uchun "Tovar kirimi" bo‘limidan 30 dona kirim qiling, "Boshqaruv" bo‘limidan smenani oching, POS da soting. Ikki filial mavjud; qoldiqlar alohida.

## Muhim cheklovlar

- Bu **lokal ishlab chiqish MVP**, production SaaS yoki qonuniy fiskal kassaning tayyor o‘rnini bosmaydi. Real do‘konga joriy qilishdan oldin audit, yuridik fiskal integratsiya, load-test, backup, monitoring va xavfsizlik tekshiruvlari kerak.
- Karta to‘lovi provayder orqali **tasdiqlanmaydi**: faqat qo‘lda qayd etiladi. Real karta tranzaksiyasi amalga oshmaydi.
- Tovar qaytarish, filiallararo transfer, inventarizatsiya, mijoz/supplier qarzi, xarajatlar, printer bridge, kamera barcode, ko‘p xodimli UI, ixtiyoriy permission, Excel import, rus/ingliz tili, hosting va offline savdo **hali yo‘q**.
- Hozirgi ombor butun son dona bilan ishlaydi. Kg/litr uchun kasr miqdor va FIFO/o‘rtacha tannarx hali aniqlanmagan.
- Xavfsiz maqsadda faqat `127.0.0.1` da ishlating. Internetga bevosita ochmang. SQLite lokal sinov uchun, production uchun PostgreSQL + migratsiyalar + qat'iy tenant isolation tavsiya qilinadi.
- DB faylni zaxiralash uchun dastur to‘xtagach `kassa.sqlite3` faylidan nusxa oling.

## API

`POST /api/login`, `GET /api/me`, `POST /api/products`, `GET /api/products?branch_id=1`, `POST /api/receipts`, `POST /api/shifts/open`, `GET /api/shifts/current?branch_id=1`, `POST /api/sales`, `POST /api/shifts/close`, `GET /api/dashboard`, `GET /api/sales`, `GET /api/sales.csv`, `GET /api/audit`.

Serverda savdo **BEGIN IMMEDIATE** tranzaksiya, qoldiq qayta tekshiruvi va `request_key` orqali idempotency bilan bajariladi. Sotuv narxi va tannarx o‘sha vaqtda snapshot tarzida saqlanadi. Ma'lumotlarga kompaniya/filial ruxsati tekshiriladi. Bu ishlab chiqish bosqichi himoyalari bo‘lib, production xavfsizlik kafolati emas.

## Keyingi bosqich

PostgreSQL / Supabase baza migratsiyasi, to‘liq role/permission modeli, qaytarish/transfer/xarajat/qarzdorlik, barcode kamera, fiskal printer testlari, to‘lov provayder va fiskal integratsiyalarni alohida ishlab chiqish kerak.

## WEB + TELEGRAM bot test (v0.2)
`WEB_BOT_TEST_QOLLANMA.md` hujjatini o‘qing. `bot.py`, `Dockerfile`, `compose.yaml`, `.env.example` qo‘shildi. Bot faqat ruxsat etilgan Telegram foydalanuvchisiga o‘qish huquqidagi savdo/qoldiq hisobotlarini beradi. Web va bot testlari `python -m pytest -q tests` orqali tekshiriladi. Webni ochiq internetga joylashtirish bu paket tarkibida avtomatik bajarilmagan.
