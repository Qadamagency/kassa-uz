# KASSA.UZ — WEB + TELEGRAM BOT test (v0.2)

## Nima tayyor?
- Web: login, kompaniya/filial tanlash, mahsulot yaratish, kirim, POS, naqd/karta **qo‘lda qayd**, smena, dashboard, savdo CSV va audit.
- Telegram: **faqat o‘qish** — `/start`, `/yordam`, `/hisobot` (bugungi Tashkent vaqtidagi savdolar), `/qoldiq` (5 donadan kam mahsulotlar).
- Bot faqat `.env` faylidagi `TELEGRAM_ALLOWED_IDS` raqamli Telegram ID lariga javob beradi va guruhdagi xabarlarni e’tiborsiz qoldiradi.
- API va bot bir xil SQLite faylidan foydalanadi. Bu **bir kompaniyali test** uchun. Bu hali SaaS production emas.

## 1. Webni lokal ishga tushirish (Docker shart emas)
1. Python 3.10+ o‘rnating. Loyihadagi `README.md` bo‘yicha kutubxonalarni o‘rnating.
2. Kuchli parol o‘rnating: PowerShell: `$env:KASSA_ADMIN_PASSWORD="OzingizTanlagan12BelgidanUzunParol!"`
3. `python app.py seed` ni bir marta bajaring.
4. `uvicorn app:app --host 127.0.0.1 --port 8000` ni ishga tushiring.
5. Brauzer: `http://127.0.0.1:8000`. Login `owner`, parol yuqorida o‘zingiz tanlagan parol.

## 2. Telegram botni ulash
1. Telegramda rasmiy `@BotFather` ga `/newbot` yuboring, bot nomi/username tanlang va **TOKEN** ni oling.
2. Raqamli Telegram **user ID** ingizni aniqlang (chat ID emas). Token va ID ni hech kimga yubormang.
3. `.env.example` dan `.env` nusxa oling, `TELEGRAM_BOT_TOKEN` va `TELEGRAM_ALLOWED_IDS` qiymatlarini qo‘ying.
4. Lokal PowerShell bilan: `$env:TELEGRAM_BOT_TOKEN="..."; $env:TELEGRAM_ALLOWED_IDS="123456789"; python bot.py`.
5. Botga shaxsiy chatda `/start`, `/hisobot`, `/qoldiq` yuboring.
Bot Telegram internet xizmatiga ulanadi. Telegram webhook emas, `getUpdates` polling ishlatadi; bitta token uchun bir dona bot protsessi kerak.

## 3. Web + bot uchun Docker Compose (test VPS)
Docker Engine va Docker Compose o‘rnatilgan VPSda:
1. `.env.example` faylidan `.env` yarating, o‘zingizning tokeningiz va Telegram user ID ingizni to‘ldiring.
2. Bir martalik yaratish: `docker compose run --rm -e KASSA_ADMIN_PASSWORD='KuchliOzingizningParolingiz123!' web python app.py seed`
3. `docker compose up -d --build`
4. Web faqat serverning `127.0.0.1:8000` manzilida eshitadi. **Jamoat internetiga 8000 portni bevosita ochmang.**
5. Ommaviy test sayt uchun HTTPS qo‘yilgan Nginx/Caddy reverse proxy va domen (yoki hosting tomonidan berilgan HTTPS URL) kerak.
6. `docker compose logs -f web bot` bilan loglarni ko‘ring.

## Muhim
- Bu test kod. Productionga chiqarishdan oldin PostgreSQL + tenant izolatsiyasi, HTTPS, rate-limit, brauzer/token xavfsizligi, zaxira nusxalar, haqiqiy to‘lov tasdiqlash, soliq/fiskal integratsiya, concurrency/load test zarur.
- Karta to‘lovi faqat qo‘lda qayd etiladi; to‘lovni karta orqali qabul qilmaydi.
- Telegram bot POS orqali sotmaydi, faqat hisobot qaytaradi.
- Windows dasturi **keyingi reliz**; hozir web mobil va desktop brauzerlarda ishlaydi.
- SQLite fayli `/data/kassa.sqlite3` Docker volume ichida; `docker compose down -v` qilsangiz baza **o‘chadi**. Oddiy `docker compose down` volume ni saqlaydi.
- Real ishlatishdan oldin huquqiy fiskal kassa talablarini rasmiy integrator bilan tekshirish zarur.
