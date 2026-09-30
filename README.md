# AI Matn Yozuvchi Bot

Telegram bot: insho, xat, tabriknoma yozadi; grammatikani tekshiradi; matnni qisqartiradi yoki kengaytiradi. Gemini API orqali ishlaydi.

## 1. Tayyorgarlik

**Telegram bot tokenini oling:**
1. Telegramda [@BotFather](https://t.me/BotFather) ga yozing.
2. `/newbot` buyrug'ini yuboring va ko'rsatmalarga amal qiling.
3. Sizga beriladigan tokenni saqlab qo'ying.

**Gemini API kalitini oling:**
1. https://aistudio.google.com/app/apikey ga kiring.
2. "Create API key" tugmasini bosing va kalitni nusxalang.

## 2. Loyihani VS Code'da ochish

1. Ushbu papkani (`ai-matn-bot`) kompyuteringizga ko'chiring va VS Code'da oching.
2. Terminalni oching (`Ctrl+` `` ` ``) va virtual muhit yarating (tavsiya etiladi):

   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS / Linux:
   source venv/bin/activate
   ```

3. Kerakli kutubxonalarni o'rnating:

   ```bash
   pip install -r requirements.txt
   ```

4. `.env.example` faylini nusxalab `.env` deb nomlang va o'z tokenlaringizni kiriting:

   ```bash
   cp .env.example .env
   ```

   `.env` faylini oching va quyidagicha to'ldiring:

   ```
   BOT_TOKEN=123456:ABC-DEF...
   GEMINI_API_KEY=AIzaSy...
   ```

## 3. Botni ishga tushirish

```bash
python bot.py
```

Konsolda `Bot ishga tushdi...` degan xabarni ko'rsangiz, bot ishlayapti. Endi Telegramda botingizni topib, `/start` buyrug'ini yuboring.

## 4. Qanday ishlaydi

- `/start` — asosiy menyuni ko'rsatadi (tugmalar bilan).
- Foydalanuvchi tugmalardan birini tanlaydi (masalan, "Insho yozish").
- Bot mavzu yoki matn so'raydi.
- Foydalanuvchi matn yuboradi → bot Gemini API'ga so'rov jo'natadi → natijani qaytaradi.
- `/menu` — istalgan vaqtda menyuni qayta ko'rsatish uchun.

## 5. Kod tuzilishi

```
ai-matn-bot/
├── bot.py            # Asosiy bot kodi
├── requirements.txt  # Python kutubxonalari
├── .env.example      # Muhit o'zgaruvchilari namunasi
└── README.md         # Ushbu fayl
```

Har bir rejim (insho, xat, tabrik, grammatika, qisqart, kengaytir) uchun alohida
"system" ko'rsatma (prompt) `bot.py` faylidagi `MODES` lug'atida saqlangan — uni
o'zgartirib, botning uslubini moslashtirishingiz mumkin.

## 6. Keyingi qadamlar (ixtiyoriy)

- **Ma'lumotlar bazasi**: foydalanuvchilar tarixini saqlash uchun SQLite yoki PostgreSQL qo'shish.
- **To'lov tizimi**: cheklangan bepul so'rovlardan keyin pullik obuna qo'shish.
- **Serverga joylashtirish**: Railway, Render yoki VPS (masalan, oddiy Ubuntu server) orqali botni 24/7 ishlatish — buning uchun `app.run_polling()` o'rniga webhook rejimidan foydalanish tavsiya etiladi.
- **Boshqa tillar**: `MODES` ichidagi promptlarni ingliz yoki rus tiliga tarjima qilib, ko'p tilli bot yaratish mumkin.
