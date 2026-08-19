import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8644696840:AAE1J15_4gsDcEkzDExqoXRCo38V5o3Nylo"
OWNER_ID = 7020448136

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Xotiradagi baza
db = {
    "users": {OWNER_ID: {"balance": 0}},
    "admins": {OWNER_ID},
    "promos": {
        "42": ["PROMO-42-TEST1", "PROMO-42-TEST2"],
        "79": ["PROMO-79-TEST1"],
        "99": [],
        "299": []
    }
}

# --- ASOSIY MENYU ---
def get_main_menu(user_id):
    keyboard = [
        [KeyboardButton(text="📦 Bulldrop")],
        [KeyboardButton(text="💳 Balans"), KeyboardButton(text="➕ Balans to'ldirish")]
    ]
    if user_id in db["admins"]:
        keyboard.append([KeyboardButton(text="👑 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# --- START KOMANDASI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0}
    await message.answer("🏠 **Bosh sahifa:**\nQuyidagi bo'limlardan birini tanlang:", reply_markup=get_main_menu(user_id), parse_mode="Markdown")

@dp.message(F.text == "🏠 Bosh menyu")
async def back_to_menu(message: types.Message):
    await message.answer("🏠 **Bosh sahifa:**", reply_markup=get_main_menu(message.from_user.id), parse_mode="Markdown")

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
    await callback.answer()

@dp.callback_query(F.data == "cancel_rules")
async def cancel_purchase(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("❌ Xarid bekor qilindi.")
    await callback.answer()

@dp.callback_query(F.data.startswith("accept_"))
async def finish_purchase(callback: types.CallbackQuery):
    code_type = callback.data.split("_")[1]
    user_id = callback.from_user.id
    
    prices = {"42": 3500, "79": 5500, "99": 8000, "299": 22000}
    price = prices[code_type]
    
    # Test uchun balansni yetarli qilamiz yoki tekshiramiz
    if db["users"][user_id]["balance"] < price:
        # Sinab ko'rishingiz uchun avtomatik balans qo'shib beramiz (test rejim)
        db["users"][user_id]["balance"] = 50000 
        
    if not db["promos"][code_type]:
        await callback.answer("❌ Afsuski, bu turdagi promokodlar hozircha qolmagan!", show_alert=True)
        return
        
    db["users"][user_id]["balance"] -= price
    promo_code = db["promos"][code_type].pop(0) # 1 ta odamga berilib bazadan o'chiriladi
    
    await callback.message.delete()
    await callback.message.answer(f"🎉 **Tabriklaymiz! Xarid muvaffaqiyatli amalga oshirildi.**\n\nSizning promokodingiz:\n`{promo_code}`", parse_mode="Markdown")
    await callback.answer()

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
        "Karta raqamiga pul o'tkazing va chekni hamda ID raqamingizni adminga yuboring.", reply_markup=markup
    )

# --- ADMIN PANEL ---
@dp.message(F.text == "👑 Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id not in db["admins"]:
        return
    keyboard = [
        [KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="🏠 Bosh menyu")]
    ]
    await message.answer("👑 **Admin boshqaruv paneli:**", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True), parse_mode="Markdown")

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id not in db["admins"]:
        return
    total_users = len(db["users"])
    await message.answer(f"📊 **Bot statistikasi:**\n\n👥 Foydalanuvchilar soni: {total_users} ta", parse_mode="Markdown")

# --- RENDER KEEP-ALIVE SERVERI ---
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

# --- RUNNER ---
async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(start_web_server())
    print("Bot 100% ishga tushdi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
