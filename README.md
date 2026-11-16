# KASSA.UZ — Web + Telegram Bot (test)

Savdo, kassa va ombor boshqaruv platformasi. Loyiha hozir **sinov bosqichida**, production/fiskal kassa emas.

## Texnologiya
- Python / FastAPI web API
- Oddiy HTML/JS frontend
- SQLite — lokal sinov uchun
- Telegram bot — faqat ruxsatli IDlar uchun hisobot

## Kodni yuklash
ChatGPT taqdim etgan `KASSA_UZ_WEB_BOT_TEST_v0_2.zip` paketini kompyuterda oching va **kassa_uz_starter papkasining ichidagi fayllarni** shu repository ildiziga yuklang. `.env`, `*.sqlite3`, token/parollarni GitHub'ga yuklamang.

## Ishga tushirish (faqat lokal test)
```bash
pip install -r requirements.txt
export KASSA_ADMIN_PASSWORD='change-this-to-a-strong-password'
python app.py seed
uvicorn app:app --host 127.0.0.1 --port 8000
```
Windows PowerShell uchun `export` o'rniga: `$env:KASSA_ADMIN_PASSWORD="your-secure-password"`.

Web: http://127.0.0.1:8000

Telegram botni ishlatish uchun maxfiy `TELEGRAM_BOT_TOKEN` va `TELEGRAM_ALLOWED_IDS` environment variables talab qilinadi.

## Internetga chiqarishdan oldin
- PostgreSQL ga o'tish va tenant/branch isolation testlari
- HTTPS, rate limiting, audit, backup va monitoring
- Backendni sinovdan o'tkazish, maxfiy parol/tokenlarni hosting env variables ichida saqlash
- Bot va web uchun alohida deploy
- Fiskal chek va to'lov provayderi integratsiyalari mavjud emas

**GitHub Pages bu Python API va Telegram botni ishga tushirmaydi.** Web backend uchun alohida hosting kerak.
