# KASSA.UZ — 8 bosqich ketma-ket rejasi (v0.5)

## Muhim yangi qarorlar — 16.11.2026
1. Har bir yangi xodim kodi tasodifiy yaratiladi, qo'lda tanlanmaydi. Masalan: `SV-4826`, `MN-6392`, `DR-2741`, `OW-9150`.
2. Prefixlar: `SV` sotuvchi, `MN` menejer, `DR` direktor, `OW` Owner. Raqam 1000–9999, kompaniya doirasida takrorlanmaydi.
3. Xodim yaratish huquqi faqat **Owner va Direktor**da. Direktor yangi sotuvchi va menejer yaratadi, Owner esa barcha lavozimlarni tayinlay oladi. Direktor o'ziga yoki boshqalarga Owner/Director vakolatini bera olmaydi.
4. Yangi xodim yaratish: ism, rol, filial, kuchli maxfiy parol/PIN o'rnatish jarayoni; kod avtomatik yaratiladi; auditga kim yaratgani yoziladi.
5. Xodim kodi maxfiy emas; kodni bilish akkauntga kirish uchun yetarli emas. Server-side login limitlash va autentifikatsiya kerak.
6. Sotuvchi o'z savdosi va shaxsiy statistikasini ko'radi; direktor barcha filiallarni, Owner barcha tizim sozlamalarini boshqaradi.

## 8 bosqich
- [ ] **1. Ma'lumotlar bazasi va xavfsizlik.** Alohida KASSA.UZ Supabase loyihasi, `database/kassa_v04_schema.sql`, `database/kassa_v05_staff_codes.sql`, default-deny RLS. **Hozir SQL kodlari GitHub'da; jonli baza hali yaratilmagan.**
- [ ] **2. Login va xodimlar kabineti.** ID+parol/PIN, session, Owner/Director xodim yaratishi, bloklash, filial permission.
- [ ] **3. Mahsulot + skaner.** O'zidagi EAN/UPC/Code128 kodlari, kamera va USB/Bluetooth skaner, unikallik tekshiruvi.
- [ ] **4. POS sotuv.** Sotuvchi ID, sana, mahsulot, ombor kamayishi, request_key, shaxsiy hisobot.
- [ ] **5. Menejer, direktor, Owner dashboardlari.** Tushum, mahsulot reytingi, sotuvchining natijasi, kengaytirilgan audit.
- [ ] **6. Ombor.** Kirim so'rovlari/tasdiqlash, qaytarish, transfer, inventarizatsiya.
- [ ] **7. Telegram bot.** Web backend yaratgan eventlar asosida ruxsatli xabarlar. Bot tokenlari GitHubga yozilmaydi.
- [ ] **8. Sinov va ilovalar.** Xavfsizlik/parallel sotuv/backup/printer testi; PWA → Windows/mobil mijozlar yagona API orqali.

## 1-bosqich qabul mezonlari
- Har bir `kassa_staff` yozuviga server orqali avtomatik prefiksli kod berilishi
- Bir kompaniyada kodlar dublikat bo'lmasligi (unique constraint va retry)
- Xodimni faqat Owner/Director endpoint orqali yarata olishi; director yuqori rollarga ko'tara olmasligi
- Sotuv ma'lumotlariga xodim/filial bog'lanishi va kompaniyalar ajratilishi
- Public/anon API orqali baza jadvallari ochilmasligi
- Test query + RLS/permission va audit sinovlari o'tishi

## Eslatma
Sxema ommaga ochiq repo ichida bo'lishi mumkin, lekin parollar, bot tokenlari, database credentials va service_role key hech qachon commit qilinmaydi. Hozirgi GitHub Pages demo faqat ko'rish uchun, real login/baza hali ishlamaydi.
