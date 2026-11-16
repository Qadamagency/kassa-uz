# KASSA.UZ — Rol va savdo modeli v0.4

> Holat: loyiha spetsifikatsiyasi va bazaning xavfsiz sxemasi GitHub'ga qo'shildi. **Baza hali Supabase'da yaratilmagan, hech qanday live login yo'q.**

## Kirish
- Xodimga noyob ko'rinadigan ID beriladi: sotuvchi `SV-2137`, menejer `MN-2137`, direktor `DR-2137`, owner `OW-2137`.
- ID taxmin qilish mumkin, shu bois **ID + maxfiy parol/PIN** shart. Serverda PIN/parol faqat kuchli hash orqali saqlanadi; urinish limiti va sessiya muddati kerak.
- Owner xodim yaratadi, filialga biriktiradi, ruxsatni bekor qiladi.
- GitHub Pages demo ID/loginni real login deb ko'rsatmasligi kerak.

## Interfeys va vakolatlar
| Rol | O'z savdosi | Barcode bilan sotuv | Ombor qoldig'i | Omborga kirim | Filial hisobotlari | Barcha filiallar | Xodim / mahsulot boshqaruvi | Audit |
|---|---|---|---|---|---|---|---|---|
| Sotuvchi | Ha | Ha | O'z filialida, cheklangan | Ruxsatli kirim so'rovi (tasdiq talab) | Yo'q | Yo'q | Yo'q | Faqat o'z operatsiyalari |
| Menejer | Ha | Ha | O'z filialida | Tasdiqlashi mumkin | Ha | Yo'q | Mahsulot qo'shish (ruxsat bo'lsa) | Filial doirasida |
| Direktor | Ha | Ha | Hammasi | Ha | Ha | Ha | Ha (xodim yaratish owner ruxsati bilan) | Hammasi |
| Owner | Ha | Ha | Hammasi | Ha | Ha | Ha | To'liq | To'liq |

**Muhim**: Omborga kirim kabi tovar sonini o'zgartiradigan amal sotuvchi tomonidan avtomatik tasdiqlanmaydi; menejer/direktor/owner tasdiqlashi kerak. Aks holda xodim qoldiqni o'zboshimchalik bilan o'zgartira oladi.

## Mahsulotning o'zidagi kod
- Mavjud EAN-8/EAN-13/UPC/Code128 shtrix-kodga asoslanamiz.
- Bitta kod kompaniya doirasida takrorlanmaydi.
- Skaner Enter yuborganda mahsulot savatga qo'shiladi; takroriy o'qish sonini oshiradi.
- Kod topilmasa sotuvchiga "topilmadi" chiqadi, mahsulot qo'shish esa menejer/direktorga jo'natiladi.
- Mahsulotning haqiqiy standart kodini QR kodga majburan almashtirmaymiz. QR ham qabul qilinishi mumkin, agar mahsulot shunday belgilangan bo'lsa.

## Har bir sotuv qaydi
- sale_id, sana/vaqt, filial_id, xodim_id, mahsulot_id, barcode snapshot, soni, ayni vaqtdagi narx va tannarx, to'lov turi, audit va stock movement.
- Sotuv + qoldiq kamayishi bitta atomar backend transaction ichida. Takroriy so'rovni `request_key` bilan bloklash.
- Sotuvchi o'zining jami sotuvini, cheklar sonini va sotilgan mahsulotlarni ko'radi.
- Menejer: qolgan qoldiq, filial tushumi, top sotilgan mahsulotlar, sotuvchilar natijasi.
- Direktor: hamma filial va xodimlar hisobotlari, kirim, o'zgartirishlar va audit tarixi.
- Owner: barcha sozlamalar, ruxsatlar, xodim va filiallar, to'liq audit.

## Keyingi implementatsiya shartlari
1. Yangi alohida KASSA.UZ Supabase loyihasini yarating (boshqa loyihalarga tegmang).
2. Database sxemasi `database/kassa_v04_schema.sql` ni yangi loyihaga migratsiya qiling.
3. Auth va backendda role/branch permission hamda RLS, tekshirilgan atomar savdo RPC yaratish.
4. Demo `demo.html`ni real Web API ga ulang. **Bundan oldin real kassada ishlatmang.**
5. USB/Bluetooth scanner va kamera testlari, test chek, parallel sotuv, qarzdorlik va rollar auditini bajaring.
