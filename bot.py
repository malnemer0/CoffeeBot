import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes
import requests

TOKEN = TOKEN = "7883952838:AAF5l5oMmySTeJa4c2wFhRx1nm2eFiF0LLg"
ADMIN_ID = 1234633064

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

user_data = {}
saved_cafes = {}
cafe_requests = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("☕ أبي كوفي", callback_data="find_coffee")],
        [InlineKeyboardButton("🔥 ترند الأسبوع", callback_data="trending")],
        [InlineKeyboardButton("❤️ كوفيهاتي المحفوظة", callback_data="saved")],
        [InlineKeyboardButton("💡 اقترح كوفي", callback_data="suggest")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "يا هلا وسهلا! ☕✨\n"
        "أنا كوفي بوت، دليلك لأحلى كوفيهات الرياض 🏙️\n\n"
        "جاهز توصلك للكوفي اللي يناسبك بثواني!\n\n"
        "ابدأ باختيار 👇",
        reply_markup=reply_markup
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "find_coffee":
        keyboard = [
            [InlineKeyboardButton("العليا", callback_data="area_العليا"),
             InlineKeyboardButton("الملقا", callback_data="area_الملقا")],
            [InlineKeyboardButton("النخيل", callback_data="area_النخيل"),
             InlineKeyboardButton("السليمانية", callback_data="area_السليمانية")],
            [InlineKeyboardButton("الروضة", callback_data="area_الروضة"),
             InlineKeyboardButton("📝 اكتب حي ثاني", callback_data="area_custom")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "أولاً، وين تقريباً؟ 📍\n\nاختار الحي أو اكتبه بنفسك 👇",
            reply_markup=reply_markup
        )

    elif query.data.startswith("area_"):
        area = query.data.replace("area_", "")
        if area == "custom":
            user_data[user_id] = {"step": "waiting_area"}
            await query.edit_message_text("اكتب اسم الحي اللي تبيه 📝")
        else:
            user_data[user_id] = {"area": area, "step": "choose_mood"}
            await show_mood(query, area)

    elif query.data.startswith("mood_"):
        mood = query.data.replace("mood_", "")
        area = user_data.get(user_id, {}).get("area", "")
        user_data[user_id]["mood"] = mood
        await query.edit_message_text("⏳ ثانية أجيبلك الأحلى...\n\n☕ → ☕☕ → ☕☕☕ جاي!")
        await show_cafes(query, area, mood, user_id)

    elif query.data.startswith("save_"):
        cafe_name = query.data.replace("save_", "")
        if user_id not in saved_cafes:
            saved_cafes[user_id] = []
        if cafe_name not in saved_cafes[user_id]:
            saved_cafes[user_id].append(cafe_name)
            await query.answer("✅ تم الحفظ!")
        else:
            await query.answer("موجود في المحفوظات!")

    elif query.data == "saved":
        await show_saved(query, user_id)

    elif query.data == "trending":
        await show_trending(query)

    elif query.data == "suggest":
        user_data[user_id] = {"step": "waiting_suggest"}
        await query.edit_message_text(
            "💡 اقتراح كوفي جديد\n\n"
            "اكتب اسم الكوفي والحي كذا:\n"
            "مثال: Noir Coffee - حي الورود\n\n"
            "📝 اكتب اقتراحك 👇"
        )

    elif query.data == "main_menu":
        await start_from_callback(query)

async def show_mood(query, area):
    keyboard = [
        [InlineKeyboardButton("🤫 هادي وأنيق", callback_data="mood_هادي")],
        [InlineKeyboardButton("🎉 صاخب وحيوي", callback_data="mood_صاخب")],
        [InlineKeyboardButton("💻 أشتغل وأقهوي", callback_data="mood_شغل")],
        [InlineKeyboardButton("👥 سهرة مع الشباب", callback_data="mood_سهرة")],
        [InlineKeyboardButton("💑 لقاء خاص", callback_data="mood_خاص")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_text(
        f"تمام! 🎯 {area} عندها كوفيهات تحفة ✨\n\nبس قولي، وش مزاجك الحين؟ 🎭",
        reply_markup=reply_markup
    )

cafes_db = {
    "العليا": [
        {"name": "Seba Coffee", "rating": 4.8, "reviews": 1243, "specialty": ["ماتشا لاتيه", "أجواء هادية", "واي فاي سريع"], "hours": "٧ص - ١٢م", "price": "٢٥-٤٠ ريال", "lat": 24.6877, "lng": 46.6860, "mood": ["هادي", "شغل"]},
        {"name": "Town Coffee", "rating": 4.6, "reviews": 987, "specialty": ["براون شوقر لاتيه", "ديكور انستقرامي", "جلسات خارجية"], "hours": "٨ص - ١ص", "price": "٢٠-٣٥ ريال", "lat": 24.6900, "lng": 46.6880, "mood": ["صاخب", "سهرة"]},
        {"name": "Black Coffee", "rating": 4.7, "reviews": 856, "specialty": ["قهوة مختصة", "هادي للشغل", "كيك محلي"], "hours": "٧ص - ١١م", "price": "٢٠-٣٥ ريال", "lat": 24.6850, "lng": 46.6840, "mood": ["هادي", "شغل", "خاص"]},
    ],
    "الملقا": [
        {"name": "Wok Coffee", "rating": 4.7, "reviews": 1100, "specialty": ["كولد برو", "أجواء عصرية", "موقع مميز"], "hours": "٧ص - ١٢م", "price": "٢٥-٤٥ ريال", "lat": 24.7700, "lng": 46.6400, "mood": ["صاخب", "سهرة"]},
        {"name": "Dose Specialty", "rating": 4.8, "reviews": 932, "specialty": ["قهوة مختصة", "هادي وأنيق", "باريستا محترف"], "hours": "٧ص - ١١م", "price": "٢٥-٤٠ ريال", "lat": 24.7720, "lng": 46.6420, "mood": ["هادي", "شغل", "خاص"]},
    ],
    "النخيل": [
        {"name": "Narrative Coffee", "rating": 4.9, "reviews": 1500, "specialty": ["أفضل قهوة مختصة", "هادي جداً", "تصميم رائع"], "hours": "٧ص - ١٢م", "price": "٣٠-٥٠ ريال", "lat": 24.7500, "lng": 46.6600, "mood": ["هادي", "خاص", "شغل"]},
        {"name": "Copper Branch", "rating": 4.6, "reviews": 780, "specialty": ["فطور مميز", "كراميل لاتيه", "جلسات واسعة"], "hours": "٧ص - ١١م", "price": "٢٠-٤٠ ريال", "lat": 24.7520, "lng": 46.6620, "mood": ["سهرة", "صاخب"]},
    ],
    "السليمانية": [
        {"name": "Felt Coffee", "rating": 4.8, "reviews": 1200, "specialty": ["بيئة إبداعية", "قهوة مختصة", "هادي للشغل"], "hours": "٧ص - ١٢م", "price": "٢٥-٤٥ ريال", "lat": 24.6800, "lng": 46.7100, "mood": ["هادي", "شغل"]},
        {"name": "Analog Coffee", "rating": 4.7, "reviews": 890, "specialty": ["أجواء كلاسيكية", "موسيقى هادية", "كيك منزلي"], "hours": "٨ص - ١١م", "price": "٢٠-٣٥ ريال", "lat": 24.6820, "lng": 46.7120, "mood": ["هادي", "خاص"]},
    ],
    "الروضة": [
        {"name": "Medd Coffee", "rating": 4.7, "reviews": 950, "specialty": ["لاتيه مميز", "جلسات خارجية", "ديكور انستقرامي"], "hours": "٧ص - ١٢م", "price": "٢٠-٤٠ ريال", "lat": 24.7000, "lng": 46.7200, "mood": ["صاخب", "سهرة"]},
        {"name": "Seven Fortunes", "rating": 4.6, "reviews": 720, "specialty": ["قهوة عربية فاخرة", "هادي وراقي", "تمور مميزة"], "hours": "٧ص - ١١م", "price": "٢٥-٤٥ ريال", "lat": 24.7020, "lng": 46.7220, "mood": ["هادي", "خاص"]},
    ],
}

async def show_cafes(query, area, mood, user_id):
    all_cafes = cafes_db.get(area, [])
    cafes = [c for c in all_cafes if mood in c.get("mood", [])]
    if not cafes:
        cafes = all_cafes

    if not cafes:
        await query.edit_message_text(
            f"ما لقينا كوفيهات في {area} الحين 😕\nجرب حي ثاني!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]])
        )
        return

    for cafe in cafes[:2]:
        name = cafe['name']
        cafe_requests[name] = cafe_requests.get(name, 0) + 1
        specialty_text = "\n".join([f"✔️ {s}" for s in cafe['specialty']])
        maps_url = f"https://maps.google.com/?q={cafe['lat']},{cafe['lng']}"

        keyboard = [
            [InlineKeyboardButton("📍 خذني للكوفي", url=maps_url),
             InlineKeyboardButton("❤️ احفظه", callback_data=f"save_{name}")],
            [InlineKeyboardButton("☕ كوفي ثاني", callback_data=f"area_{area}"),
             InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        trend_count = cafe_requests.get(name, 0)
        trend_text = f"\n\n🔥 طُلب {trend_count} مرة هذا الأسبوع! 📈" if trend_count > 5 else ""

        text = (
            f"✨━━━━━━━━━━━━━━━━━━✨\n\n"
            f"☕  {name}  ☕\n"
            f"        {area}، الرياض\n\n"
            f"✨━━━━━━━━━━━━━━━━━━✨\n\n"
            f"⭐️ {cafe['rating']}  |  👥 {cafe['reviews']:,} تقييم\n\n"
            f"━━━━━━━━━━━━━━━━━━\n\n"
            f"🌟 ليش مميز؟\n"
            f"{specialty_text}\n\n"
            f"⏰ الدوام: {cafe['hours']}\n"
            f"💰 المعدل: {cafe['price']}"
            f"{trend_text}\n\n"
            f"✨━━━━━━━━━━━━━━━━━━✨"
        )
        await query.message.reply_text(text, reply_markup=reply_markup)

async def show_saved(query, user_id):
    saved = saved_cafes.get(user_id, [])
    if not saved:
        keyboard = [[InlineKeyboardButton("☕ ابحث عن كوفي", callback_data="find_coffee")]]
        await query.edit_message_text(
            "ما عندك كوفيهات محفوظة بعد! ❤️\nابدأ البحث وحفظ اللي يعجبك 😊",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    text = "❤️━━━━━━━━━━━━━━━━━━❤️\n\n"
    text += f"    كوفيهاتي المحفوظة\n    عندك {len(saved)} كوفيهات 📋\n\n"
    text += "❤️━━━━━━━━━━━━━━━━━━❤️\n\n"
    for i, cafe in enumerate(saved, 1):
        text += f"{i}️⃣ {cafe}\n"

    keyboard = [[InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def show_trending(query):
    if not cafe_requests:
        await query.edit_message_text(
            "🔥 ما في ترند بعد!\nابدأ البحث عن كوفيهات عشان يتكون الترند 😊",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("☕ ابحث", callback_data="find_coffee")]])
        )
        return

    sorted_cafes = sorted(cafe_requests.items(), key=lambda x: x[1], reverse=True)[:3]
    medals = ["🥇", "🥈", "🥉"]
    text = "🔥━━━━━━━━━━━━━━━━━━🔥\n\n"
    text += "    ترند الأسبوع ☕\n\n"
    text += "🔥━━━━━━━━━━━━━━━━━━🔥\n\n"
    for i, (cafe, count) in enumerate(sorted_cafes):
        text += f"{medals[i]} {cafe}\n   {count} طلب هذا الأسبوع\n\n"

    keyboard = [
        [InlineKeyboardButton("☕ ابحث في حيك", callback_data="find_coffee")],
        [InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]
    ]
    await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text
    step = user_data.get(user_id, {}).get("step", "")

    if step == "waiting_area":
        area = text
        user_data[user_id] = {"area": area, "step": "choose_mood"}
        keyboard = [
            [InlineKeyboardButton("🤫 هادي وأنيق", callback_data="mood_هادي")],
            [InlineKeyboardButton("🎉 صاخب وحيوي", callback_data="mood_صاخب")],
            [InlineKeyboardButton("💻 أشتغل وأقهوي", callback_data="mood_شغل")],
            [InlineKeyboardButton("👥 سهرة مع الشباب", callback_data="mood_سهرة")],
            [InlineKeyboardButton("💑 لقاء خاص", callback_data="mood_خاص")]
        ]
        await update.message.reply_text(
            f"تمام! 🎯 {area} عندها كوفيهات تحفة ✨\n\nوش مزاجك الحين؟ 🎭",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    elif step == "waiting_suggest":
        suggestion = text
        username = update.message.from_user.username or "بدون يوزر"
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"💡 اقتراح كوفي جديد!\n\n"
                f"👤 المستخدم: @{username}\n"
                f"🆔 ID: {user_id}\n"
                f"☕ الاقتراح: {suggestion}"
            )
        )
        user_data[user_id] = {}
        keyboard = [[InlineKeyboardButton("🏠 الرئيسية", callback_data="main_menu")]]
        await update.message.reply_text(
            "✅ شكراً على اقتراحك!\n"
            "راح نراجعه ونضيفه قريباً إن شاء الله ☕",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    else:
        await start(update, context)

async def start_from_callback(query):
    keyboard = [
        [InlineKeyboardButton("☕ أبي كوفي", callback_data="find_coffee")],
        [InlineKeyboardButton("🔥 ترند الأسبوع", callback_data="trending")],
        [InlineKeyboardButton("❤️ كوفيهاتي المحفوظة", callback_data="saved")],
        [InlineKeyboardButton("💡 اقترح كوفي", callback_data="suggest")]
    ]
    await query.edit_message_text(
        "يا هلا وسهلا! ☕✨\n"
        "أنا كوفي بوت، دليلك لأحلى كوفيهات الرياض 🏙️\n\n"
        "ابدأ باختيار 👇",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    print("✅ البوت شغال!")
    app.run_polling()

if __name__ == "__main__":
    main()