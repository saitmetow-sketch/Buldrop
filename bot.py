import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8722191945:AAEk8N820FibWw8lLJ6sgzD_BID50BCVDbo"
OWNER_ID = 7020448136

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bazani xotirada saqlash uchun vaqtinchalik tuzilmalar (Keyinchalik SQL ulasa bo'ladi)
db = {
    "users": {OWNER_ID: {"balance": 0}},
    "admins": {OWNER_ID},
    "balance_admins": {OWNER_ID},
    "channels": [],       # Majburiy obuna kanallari: [{"id": ..., "url": ..., "title": ...}]
    "req_channels": [],   # So'rovli obuna kanallari
    "promos": {
        "42": [],
        "79": [],
        "99": [],
        "299": []
    }
}

# --- OBUNANI TEKSHIRISH ---
async def check_subscriptions(user_id: int) -> bool:
    # Majburiy va so'rovli obunalarni tekshirish mantiqi
    for ch in db["channels"]:
        try:
            member = await bot.get_chat_member(chat_id=ch["id"], user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
            pass
    return True

# --- /START KOMANDASI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0}

    is_sub = await check_subscriptions(user_id)
    if not is_sub and db["channels"]:
        keyboard = []
        for ch in db["channels"]:
            keyboard.append([InlineKeyboardButton(text=f"📢 {ch['title']}", url=ch["url"])])
        keyboard.append([InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub")])
        await message.answer("⚠️ Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))
    else:
        await send_main_menu(message)

@dp.callback_query(F.data == "check_sub")
async def process_check(callback: types.CallbackQuery):
    if await check_subscriptions(callback.from_user.id):
        await callback.message.delete()
        await send_main_menu(callback.message)
    else:
        await callback.answer("❌ Hamma kanallarga obuna bo'lmadingiz!", show_alert=True)

# --- ASOSIY MENYU ---
async def send_main_menu(message: types.Message):
    keyboard = [
        [KeyboardButton(text="📦 Bulldrop")],
        [KeyboardButton(text="💳 Balans"), KeyboardButton(text="➕ Balans to'ldirish")]
    ]
    if message.from_user.id in db["admins"]:
        keyboard.append([KeyboardButton(text="👑 Admin Panel")])
        
    markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await message.answer("🏠 **Bosh sahifa:**\nQuyidagi bo'limlardan birini tanlang:", reply_markup=markup, parse_mode="Markdown")

@dp.message(F.text == "🏠 Bosh menyu")
async def back_to_menu(message: types.Message):
    await send_main_menu(message)

# --- BULLDROP BO'LIMI ---
@dp.message(F.text == "📦 Bulldrop")
async def bulldrop_menu(message: types.Message):
    p42 = len(db["promos"]["42"])
    p79 = len(db["promos"]["79"])
    p99 = len(db["promos"]["99"])
    p299 = len(db["promos"]["299"])

    keyboard = [
        [InlineKeyboardButton(text=f"🎁 42 – 3,500 so'm ({p42} ta bor)", callback_data="buy_42")],
        [InlineKeyboardButton(text=f"🎁 79 – 5,500 so'm ({p79} ta bor)", callback_data="buy_79")],
        [InlineKeyboardButton(text=f"🎁 99 – 8,000 so'm ({p99} ta bor)", callback_data="buy_99")],
        [InlineKeyboardButton(text=f"🎁 299 – 22,000 so'm ({p299} ta bor)", callback_data="buy_299")]
    ]
    await message.answer("📦 **Bulldrop uchun promokodlar narxlari:**\nSotib olmoqchi bo'lgan promokodingizni tanlang:", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

@dp.callback_query(F.data.startswith("buy_"))
async def ask_rules(callback: types.CallbackQuery):
    code_type = callback.data.split("_")[1]
    rule_text = (
        "⚠️ **Muhim xarid qoidasi!**\n\n"
        "📹 Xarid qilish tugmasini bosishdan oldin uzluksiz ekran videosini (Screen Record) yoqing!\n\n"
        "Videoda botdan kod olinishi, nusxalanib (Copy) darhol saytga qo'yilishi (Paste) va faollashtirilishi kesilmasdan ko'rinishi shart.\n\n"
        "Aks holda \"ishlamadi\" yoki \"ishlatilgan\" degan e'tirozlar ko'rib chiqilmaydi va pul qaytarilmaydi."
    )
    keyboard = [
        [InlineKeyboardButton(text="✅ Roziman", callback_data=f"accept_{code_type}"),
         InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel_rules")]
    ]
    await callback.message.answer(rule_text, reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard), parse_mode="Markdown")

@dp.callback_query(F.data == "cancel_rules")
async def cancel_purchase(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("❌ Xarid bekor qilindi.")

@dp.callback_query(F.data.startswith("accept_"))
async def finish_purchase(callback: types.CallbackQuery):
    code_type = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    prices = {"42": 3500, "79": 5500, "99": 8000, "299": 22000}
    price = prices[code_type]
    
    if db["users"][user_id]["balance"] < price:
        await callback.answer("❌ Balansingizda yetarli mablag' yo'q!", show_alert=True)
        return
        
    if not db["promos"][code_type]:
        await callback.answer("❌ Afsuski, bu turdagi promokodlar hozircha qolmagan!", show_alert=True)
        return
        
    # Balansdan yechish va promokod berish
    db["users"][user_id]["balance"] -= price
    promo_code = db["promos"][code_type].pop(0) # 1 ta odamga berilib, bazadan o'chiriladi
    
    await callback.message.delete()
    await callback.message.answer(f"🎉 **Tabriklaymiz! Xarid muvaffaqiyatli amalga oshirildi.**\n\nSizning promokodingiz:\n`{promo_code}`", parse_mode="Markdown")

# --- BALANS VA TO'LDIRISH ---
@dp.message(F.text == "💳 Balans")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    bal = db["users"].get(user_id, {}).get("balance", 0)
    await message.answer(f"🆔 ID: `{user_id}`\n💰 Balansingiz: **{bal} so'm**", parse_mode="Markdown")

@dp.message(F.text == "➕ Balans to'ldirish")
async def top_up_balance(message: types.Message):
    keyboard = [[KeyboardButton(text="🏠 Bosh menyu")]]
    markup = ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)
    await message.answer(
        "💳 Balansni to'ldirish uchun:\n\n"
        "Karta raqamiga pul o'tkazing va chekni hamda ID raqamingizni adminlarga yuboring.\n"
        "(@Admin ga murojaat qiling)", reply_markup=markup
    )

# --- ADMIN PANEL ---
@dp.message(F.text == "👑 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id not in db["admins"]:
        return
    keyboard = [
        [KeyboardButton(text="➕ Promokod qo'shish"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="📢 Kanal qo'shish"), KeyboardButton(text="🗑 Kanal o'chirish")],
        [KeyboardButton(text="👤 Admin qo'shish"), KeyboardButton(text="❌ Adminni ayirish")],
        [KeyboardButton(text="🏠 Bosh menyu")]
    ]
    await message.answer("👑 **Admin boshqaruv paneli:**", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True), parse_mode="Markdown")

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id not in db["admins"]:
        return
    total_users = len(db["users"])
    await message.answer(f"📊 **Bot statistikasi:**\n\n👥 Foydalanuvchilar soni: {total_users} ta", parse_mode="Markdown")

@dp.message(F.text == "➕ Promokod qo'shish")
async def add_promo_start(message: types.Message):
    if message.from_user.id not in db["admins"]:
        return
    keyboard = [
        [InlineKeyboardButton(text="42", callback_data="add_p_42"), InlineKeyboardButton(text="79", callback_data="add_p_79")],
        [InlineKeyboardButton(text="99", callback_data="add_p_99"), InlineKeyboardButton(text="299", callback_data="add_p_299")]
    ]
    await message.answer("Qaysi turdagi promokod qo'shmoqchisiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# (Admin qo'shish, kanal qo'shish va promokod matnini qabul qilish qismlarini FSM yoki oddiy holatda kengaytirib olasiz)

# --- 5 DAQIQADAN UYG'OTIB TURUVCHI WEB SERVER (RENDER / HOSTING UCHUN) ---
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", 8080)
    await site.start()

# --- ASOSIY RUNNER ---
async def main():
    # Keep-alive veb serverini ishga tushirish
    asyncio.create_task(start_web_server())
    
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

