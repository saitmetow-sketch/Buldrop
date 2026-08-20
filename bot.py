import json
import os
import telebot
from telebot import types

TOKEN = "8644696840:AAFhsRFaMsz8XrySdMV4kAVAJ4RbITaJT34"
bot = telebot.TeleBot(TOKEN)

DB_FILE = "database.json"

# Asosiy bazani yaratish yoki yuklash
def load_db():
    if not os.path.exists(DB_FILE):
        default_data = {
            "users": {},  # user_id: {"balance": 0, "username": "..."}
            "channels": [],  # {"id": "@kanal", "type": "mandatory"/"request"}
            "admins": [],  # admin_id lar
            "balance_admins": [],  # Hisob to'ldiruvchi admin id lari
            "buldrops": {"1": 10, "2": 5, "3": 2, "4": 0},  # 4 ta son va ularning miqdori
            "history": []  # Tarix uchun
        }
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(default_data, f, ensure_ascii=False, indent=4)
    with open(DB_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def log_history(text):
    db = load_db()
    db["history"].append(text)
    save_db(db)

# Obunani tekshirish funksiyasi
def check_subscriptions(user_id):
    db = load_db()
    channels = db["channels"]
    not_subscribed = []
    
    for ch in channels:
        channel_id = ch["id"]
        try:
            member = bot.get_chat_member(channel_id, user_id)
            if member.status not in ['member', 'administrator', 'creator']:
                not_subscribed.append(channel_id)
        except Exception:
            # Agar bot kanalga qo'shilmagan bo'lsa yoki xatolik bo'lsa o'tkazib yubormaslik uchun
            not_subscribed.append(channel_id)
    return not_subscribed

# Start komandasi
@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    db = load_db()
    
    if str(user_id) not in db["users"]:
        db["users"][str(user_id)] = {"balance": 0, "username": message.from_user.username or "Noma'lum"}
        save_db(db)
        log_history(f"Yangi foydalanuvchi: {user_id}")

    not_sub = check_subscriptions(user_id)
    if not_sub:
        markup = types.InlineKeyboardMarkup()
        for ch in not_sub:
            markup.add(types.InlineKeyboardButton(f"Obuna bo'lish 📢", url=f"https://t.me/{ch.replace('@', '')}"))
        markup.add(types.InlineKeyboardButton("✅ Obunani tekshirish", callback_data="check_sub"))
        bot.send_message(message.chat.id, "Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=markup)
    else:
        show_main_menu(message.chat.id, user_id)

@bot.callback_query_handler(func=lambda call: call.data == "check_sub")
def callback_check_sub(call):
    user_id = call.from_user.id
    not_sub = check_subscriptions(user_id)
    if not_sub:
        bot.answer_callback_query(call.id, "Hamma kanalga obuna bo'linmadi ❌", show_alert=True)
    else:
        bot.answer_callback_query(call.id, "Rahmat, obuna tasdiqlandi ✅")
        bot.delete_message(call.message.chat.id, call.message.message_id)
        show_main_menu(call.message.chat.id, user_id)

def show_main_menu(chat_id, user_id):
    db = load_db()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🎁 Buldrop", "💳 Balansni to'ldirish")
    
    # Oddiy admin yoki owner tekshiruvi
    if user_id in db["admins"] or user_id in db["balance_admins"] or str(user_id) == str(list(db["users"].keys())[0]): # misol uchun 1-foydalanuvchi yoki owner
        markup.add("🛠 Admin panel")
    
    # Owner uchun maxsus tugma (kodda o'zingizning Telegram ID raqamingizni yozib qo'yishingiz mumkin)
    OWNER_ID = 123456789 # O'z ID raqamingizni yozing
    if user_id == OWNER_ID or str(user_id) in [str(x) for x in db.get("owners", [])]:
        markup.add("👑 Owner menyu")

    bot.send_message(chat_id, "Asosiy menyushiga xush kelibsiz:", reply_markup=markup)

# Tugmalar bosilganda
@bot.message_handler(func=lambda message: True)
def handle_text(message):
    user_id = message.from_user.id
    text = message.text
    db = load_db()

    if text == "🎁 Buldrop":
        buldrops = db["buldrops"]
        msg = "🎁 **Buldrop ma'lumotlari:**\n\n"
        for k, v in buldrops.items( ):
            msg += f"• {k}-son: {v} ta mavjud\n"
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")

    elif text == "💳 Balansni to'ldirish":
        if db["balance_admins"]:
            # Hisob to'ldiruvchi adminning userini chiqarish
            b_admin_id = db["balance_admins"][0]
            try:
                chat_info = bot.get_chat(b_admin_id)
                username = chat_info.username
                if username:
                    bot.send_message(message.chat.id, f"💳 Balansni to'ldirish uchun hisob adminiga yozing: @{username}\n🆔 ID: {b_admin_id}")
                else:
                    bot.send_message(message.chat.id, f"💳 Balansni to'ldirish uchun hisob adminiga yozing: tg://user?id={b_admin_id}")
            except:
                bot.send_message(message.chat.id, "Hozirda hisob admini topilmadi.")
        else:
            bot.send_message(message.chat.id, "Hozirda hisob to'ldirish admini tayinlanmagan.")

    elif text == "🛠 Admin panel":
        if user_id in db["admins"] or user_id in db["balance_admins"]:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("➕ Majburiy kanal qo'shish", "➖ Majburiy kanal o'chirish")
            markup.add("➕ So'rovli kanal qo'shish", "➖ So'rovli kanal o'chirish")
            markup.add("📊 Statistika", "📤 Xabar yuborish")
            markup.add("📢 Reklama yuborish", "❌ Reklama o'chirish")
            markup.add("💰 Balansni o'zgartirish", "🔙 Orqaga")
            bot.send_message(message.chat.id, "Admin panelga xush kelibsiz:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Sizda admin huquqi yo'q.")

    elif text == "👑 Owner menyu":
        OWNER_ID = 123456789 # O'zingizning ID raqamingiz
        if user_id == OWNER_ID:
            markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
            markup.add("➕ Admin qo'shish", "➖ Admin o'chirish")
            markup.add("➕ Hisob admini qo'shish", "➖ Hisob admini o'chirish")
            markup.add("📜 Tarix bo'limi", "🔙 Orqaga")
            bot.send_message(message.chat.id, "Owner menyusiga xush kelibsiz:", reply_markup=markup)
        else:
            bot.send_message(message.chat.id, "Bu menyu faqat bot egasi uchun!")

    elif text == "🔙 Orqaga":
        show_main_menu(message.chat.id, user_id)

    elif text == "📜 Tarix bo'limi":
        if user_id == 123456789: # Owner tekshiruvi
            history_text = "\n".join(db["history"][-20:]) # Oxirgi 20 ta harakat
            bot.send_message(message.chat.id, f"📜 **Bot tarixi (oxirgi amallar):**\n\n{history_text or 'Hozircha tarix bo\'sh'}", parse_mode="Markdown")

    elif text == "📊 Statistika":
        users_count = len(db["users"])
        channels_count = len(db["channels"])
        bot.send_message(message.chat.id, f"📊 **Statistika:**\n\n👥 Foydalanuvchilar soni: {users_count}\n📢 Kanallar soni: {channels_count}", parse_mode="Markdown")

    elif text == "💰 Balansni o'zgartirish":
        msg = bot.send_message(message.chat.id, "Foydalanuvchi ID raqami va qo'shiladigan/ayiriladigan summani yuboring:\nFormat: `ID summa` (Masalan: `12345678 500` yoki `-200`)", parse_mode="Markdown")
        bot.register_next_step_handler(msg, process_change_balance)

def process_change_balance(message):
    try:
        parts = message.text.split()
        target_id = parts[0]
        amount = int(parts[1])
        db = load_db()
        if target_id in db["users"]:
            db["users"][target_id]["balance"] += amount
            save_db(db)
            bot.send_message(message.chat.id, f"Muvaffaqiyatli! Foydalanuvchi balansi o'zgartirildi.")
            log_history(f"Admin {message.from_user.id} user {target_id} balansini {amount} ga o'zgartirdi.")
        else:
            bot.send_message(message.chat.id, "Foydalanuvchi topilmadi.")
    except Exception:
        bot.send_message(message.chat.id, "Xato format! Qaytadan urinib ko'ring.")

# Botni ishga tushirish
if __name__ == "__main__":
    print("Bot ishga tushdi...")
    bot.infinity_polling()
