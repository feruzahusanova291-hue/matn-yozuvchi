"""
AI Matn Yozuvchi Bot
--------------------
Telegram bot: insho, xat, tabrik yozadi; grammatikani tekshiradi;
matnni qisqartiradi yoki kengaytiradi.

Ishlatilgan kutubxonalar:
    - python-telegram-bot (v20+, async)
    - google-generativeai (Gemini API)

Ishga tushirish:
    1) .env faylini to'ldiring (BOT_TOKEN va GEMINI_API_KEY)
    2) pip install -r requirements.txt
    3) python bot.py
"""

import asyncio
import logging
import os
import time

import requests
from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.request import HTTPXRequest
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

# --------------------------------------------------------------------------
# Sozlamalar
# --------------------------------------------------------------------------

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. .env faylini tekshiring.")
if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY topilmadi. .env faylini tekshiring.")

# Barqaror modellar ro'yxati (biri 503 yoki band bo'lsa, zaxiradagilariga o'tadi)
FALLBACK_MODELS = [
    GEMINI_MODEL,
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-3.5-flash",
]
MODELS_TO_TRY = list(dict.fromkeys(FALLBACK_MODELS))

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# Har bir foydalanuvchi uchun tanlangan rejimni saqlaymiz (RAMda, oddiy holat)
# context.user_data["mode"] qiymatlari:
#   "insho" | "xat" | "tabrik" | "grammatika" | "qisqart" | "kengaytir"

MODES = {
    "insho": {
        "title": "📝 Insho yozish",
        "prompt": (
            "Mavzuni yuboring, men shu mavzuda o'zbek tilida chiroyli, "
            "mantiqiy tuzilgan insho yozib beraman.\n\n"
            "Masalan: <i>Vatanga muhabbat</i>"
        ),
        "system": (
            "Sen tajribali o'zbek tili va adabiyoti o'qituvchisisan. "
            "Foydalanuvchi bergan mavzuda o'zbek tilida, sodda, boy va tushunarli "
            "tilda, kirish-asosiy qism-xulosa tuzilishiga ega to'liq insho yoz. "
            "Insho 250-400 so'z atrofida bo'lsin. Har bir gap va fikrni oxirigacha to'liq yakunla. "
            "Insho oxirida hech qanday ortiqcha so'z sanash, hisobot yoki tahlil qo'shma, faqat inshoning o'zini yoz."
        ),
    },
    "xat": {
        "title": "✉️ Xat yozish",
        "prompt": (
            "Xat kimga va nima haqida ekanini yozing.\n\n"
            "Masalan: <i>Do'stimga tug'ilgan kuni tabrigi bilan bog'liq xat</i> "
            "yoki <i>Ish beruvchiga rasmiy ariza xati</i>"
        ),
        "system": (
            "Sen professional yozuvchisan. Foydalanuvchi bergan tavsifga "
            "asoslanib, o'zbek tilida to'liq, tarkibi to'g'ri (murojaat, "
            "asosiy matn, yakunlovchi qism, imzo) xat yoz. Gaplarni to'liq yakunla. "
            "Uslubni vaziyatga mos tanla (rasmiy yoki norasmiy). Ortiqcha izoh qo'shma."
        ),
    },
    "tabrik": {
        "title": "🎉 Tabriknoma yozish",
        "prompt": (
            "Qanday tabrik va kim uchun ekanini yozing.\n\n"
            "Masalan: <i>Onamning tug'ilgan kuniga iliq tabrik</i>"
        ),
        "system": (
            "Sen ijodkor tabrik matnlari yozuvchisisan. Foydalanuvchi bergan "
            "vaziyat uchun o'zbek tilida samimiy, chiroyli va ta'sirchan tabrik "
            "matni yoz (5-10 gap). Gaplarni to'liq yakunla. Ortiqcha izoh qo'shma."
        ),
    },
    "grammatika": {
        "title": "✅ Grammatikani tekshirish",
        "prompt": "Tekshirilishi kerak bo'lgan matnni yuboring.",
        "system": (
            "Sen o'zbek tili grammatikasi bo'yicha mutaxassissan. Foydalanuvchi "
            "yuborgan matndagi imlo, punktuatsiya va grammatik xatolarni top. "
            "Javobni ikki qismda ber: 1) 'Tuzatilgan matn:' sarlavhasi ostida "
            "to'g'rilangan matnning to'liq nusxasi, 2) 'Xatolar tahlili:' "
            "sarlavhasi ostida topilgan xatolar va ular qanday tuzatilgani "
            "haqida qisqa ro'yxat."
        ),
    },
    "qisqart": {
        "title": "✂️ Matnni qisqartirish",
        "prompt": "Qisqartirilishi kerak bo'lgan matnni yuboring.",
        "system": (
            "Sen matn muharrirsan. Foydalanuvchi yuborgan matnni ma'nosini "
            "yo'qotmagan holda, taxminan 2-3 baravar qisqartirib, o'zbek "
            "tilida qayta yoz. Faqat qisqartirilgan matnni qaytar, ortiqcha "
            "izoh berma."
        ),
    },
    "kengaytir": {
        "title": "📖 Matnni kengaytirish",
        "prompt": "Kengaytirilishi kerak bo'lgan matnni yuboring.",
        "system": (
            "Sen matn muharrirsan. Foydalanuvchi yuborgan matnni asosiy "
            "g'oyasini saqlagan holda, tafsilotlar, misollar va izohlar "
            "qo'shib, o'zbek tilida 2-3 baravar kengaytirib yoz. Faqat "
            "kengaytirilgan matnni qaytar, ortiqcha izoh berma."
        ),
    },
}


# --------------------------------------------------------------------------
# Gemini bilan ishlash
# --------------------------------------------------------------------------


def _call_gemini_sync(system_instruction: str, user_text: str) -> str:
    """Gemini REST API'ga zaxira modellar va qayta urinish bilan so'rov yuboradi."""
    full_prompt = f"{system_instruction}\n\nFoydalanuvchi matni:\n{user_text}"
    payload = {
        "contents": [{"parts": [{"text": full_prompt}]}],
        "generationConfig": {
            "temperature": 0.7,
            "maxOutputTokens": 8192,
        },
    }

    last_error = "Noma'lum xatolik"
    for model_name in MODELS_TO_TRY:
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model_name}:generateContent"
        )
        for attempt in range(2):
            try:
                response = requests.post(
                    url,
                    json=payload,
                    headers={
                        "x-goog-api-key": GEMINI_API_KEY,
                        "Content-Type": "application/json",
                    },
                    timeout=35,
                )
                if response.status_code == 200:
                    data = response.json()
                    candidates = data.get("candidates") or []
                    if not candidates:
                        reason = data.get("promptFeedback", {}).get("blockReason", "xavfsizlik filtri")
                        raise ValueError(f"Gemini javob qaytarmadi ({reason})")

                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = "".join(
                        part.get("text", "") for part in parts if not part.get("thought", False)
                    ).strip()
                    if not text:
                        text = "".join(part.get("text", "") for part in parts).strip()
                    if text:
                        return text

                logger.warning(
                    "Model %s xatolik qaytardi: HTTP %s (urinish %s/2)",
                    model_name,
                    response.status_code,
                    attempt + 1,
                )
                last_error = f"HTTP {response.status_code}"
                time.sleep(0.5)
            except requests.exceptions.RequestException as err:
                logger.warning("Model %s ulanish xatosi: %s", model_name, err)
                last_error = str(err)
                time.sleep(0.5)

    raise RuntimeError(f"Barcha modellar band yoki javob bermadi ({last_error})")


async def ask_gemini(system_instruction: str, user_text: str) -> str:
    """Gemini API'ga so'rov yuboradi va matn javobini qaytaradi (asinxron o'ram)."""
    try:
        return await asyncio.to_thread(_call_gemini_sync, system_instruction, user_text)
    except Exception as exc:
        logger.exception("Gemini API so'rovida xatolik: %s", exc)
        return (
            "⚠️ Hozirda AI xizmatida yuqori yuklama kuzatilmoqda. "
            "Iltimos, bir oz kuting va xabaringizni qaytadan yuboring."
        )


# --------------------------------------------------------------------------
# Telegram handlerlar
# --------------------------------------------------------------------------


def main_menu_keyboard() -> InlineKeyboardMarkup:
    buttons = [
        [InlineKeyboardButton(MODES["insho"]["title"], callback_data="insho")],
        [InlineKeyboardButton(MODES["xat"]["title"], callback_data="xat")],
        [InlineKeyboardButton(MODES["tabrik"]["title"], callback_data="tabrik")],
        [InlineKeyboardButton(MODES["grammatika"]["title"], callback_data="grammatika")],
        [InlineKeyboardButton(MODES["qisqart"]["title"], callback_data="qisqart")],
        [InlineKeyboardButton(MODES["kengaytir"]["title"], callback_data="kengaytir")],
    ]
    return InlineKeyboardMarkup(buttons)


def back_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [[InlineKeyboardButton("⬅️ Asosiy menyuga qaytish", callback_data="main_menu")]]
    )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("mode", None)
    text = (
        "👋 Salom! Men <b>AI Matn Yozuvchi Bot</b>man.\n\n"
        "Men quyidagilarni qila olaman:\n"
        "• Insho, xat va tabriknoma yozish\n"
        "• Matningizdagi grammatik xatolarni tekshirish\n"
        "• Matnni qisqartirish yoki kengaytirish\n\n"
        "Quyidagi menyudan kerakli bo'limni tanlang 👇"
    )
    await update.message.reply_text(
        text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Bo'limni tanlang 👇", reply_markup=main_menu_keyboard()
    )


async def on_menu_click(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    mode = query.data
    if mode == "main_menu":
        context.user_data.pop("mode", None)
        text = (
            "👋 Salom! Men <b>AI Matn Yozuvchi Bot</b>man.\n\n"
            "Men quyidagilarni qila olaman:\n"
            "• Insho, xat va tabriknoma yozish\n"
            "• Matningizdagi grammatik xatolarni tekshirish\n"
            "• Matnni qisqartirish yoki kengaytirish\n\n"
            "Quyidagi menyudan kerakli bo'limni tanlang 👇"
        )
        await query.edit_message_text(
            text, reply_markup=main_menu_keyboard(), parse_mode=ParseMode.HTML
        )
        return

    if mode not in MODES:
        return

    context.user_data["mode"] = mode
    await query.edit_message_text(
        f"<b>{MODES[mode]['title']}</b>\n\n{MODES[mode]['prompt']}\n\n"
        "<i>Bekor qilish uchun quyidagi tugmani bosing yoki /start buyrug'ini yuboring.</i>",
        reply_markup=back_keyboard(),
        parse_mode=ParseMode.HTML,
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    mode = context.user_data.get("mode")

    if not mode:
        await update.message.reply_text(
            "Iltimos, avval bo'limni tanlang 👇",
            reply_markup=main_menu_keyboard(),
        )
        return

    user_text = update.message.text
    logger.info("Yangi so'rov: user_id=%s, rejim=%s, matn=%r", update.effective_user.id, mode, user_text[:60])
    thinking_msg = await update.message.reply_text("⏳ Yozilmoqda, biroz kuting...")

    result = await ask_gemini(MODES[mode]["system"], user_text)

    # Telegram xabar uzunligi cheklovi (4096 belgi) — kerak bo'lsa bo'lib yuboramiz
    max_len = 4000
    chunks = [result[i : i + max_len] for i in range(0, len(result), max_len)] or [
        "Bo'sh javob qaytdi, qayta urinib ko'ring."
    ]

    try:
        await thinking_msg.delete()
    except Exception:
        pass

    for chunk in chunks:
        try:
            await update.message.reply_text(chunk, parse_mode=ParseMode.MARKDOWN)
        except Exception:
            await update.message.reply_text(chunk)

    await update.message.reply_text(
        "Yana biror amal tanlaysizmi?", reply_markup=main_menu_keyboard()
    )
    context.user_data.pop("mode", None)


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.error("Xatolik yuz berdi", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        try:
            await update.effective_message.reply_text(
                "❌ Xatolik yuz berdi. Iltimos, qayta urinib ko'ring yoki /start bosing."
            )
        except Exception:
            pass


# --------------------------------------------------------------------------
# Ishga tushirish
# --------------------------------------------------------------------------


def main() -> None:
    request = HTTPXRequest(
        connect_timeout=30.0,
        read_timeout=30.0,
        write_timeout=30.0,
        pool_timeout=30.0,
    )
    app = Application.builder().token(BOT_TOKEN).request(request).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CallbackQueryHandler(on_menu_click))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
    app.add_error_handler(on_error)

    logger.info("Bot ishga tushdi...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    try:
        main()
    except (KeyboardInterrupt, SystemExit):
        logger.info("Bot to'xtatildi.")
    except Exception:
        import traceback
        traceback.print_exc()
        input("\n[DEBUG] Dastur tugadi. Chiqish uchun Enter bosing...")
