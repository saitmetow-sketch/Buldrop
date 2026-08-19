import asyncio
import logging
import os
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

# --- ASOSIY SOZLAMALAR ---
# Yangi token joylashtirildi
TOKEN = "8644696840:AAE1J15_4gsDcEkzDExqoXRCo38V5o3Nylo"
OWNER_ID = 7020448136

bot = Bot(token=TOKEN)
dp = Dispatcher()

# Bazani xotirada saqlash
db = {
    "users": {OWNER_ID: {"balance": 0}},
    "admins": {OWNER_ID},
    "channels": [], 
    "promos": {
        "42": [],
        "79": [],
        "99": [],
        "299": []
    }
}

# --- OBUNANI TEKSHIRISH ---
async def check_subscriptions(user_id: int) -> bool:
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

    # Asosiy menyuni ko'rsatish
    await send_main_menu(message)

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

# --- BULLDROP ---
@dp.message(F.text == "📦 Bulldrop")
async def bulldrop_menu(message: types.Message):
    keyboard = [
        [InlineKeyboardButton(text="🎁 42 – 3,500 so'm", callback_data="buy_42")],
        [InlineKeyboardButton(text="🎁 79 – 5,500 so'm", callback_data="buy_79")],
        [InlineKeyboardButton(text="🎁 99 – 8,000 so'm", callback_data="buy_99")],
        [InlineKeyboardButton(text="🎁 299 – 22,000 so'm", callback_data="buy_299")]
    ]
    await message.answer("📦 **Bulldrop promokodlari:**", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

# --- RENDER KEEP-ALIVE SERVERI ---
async def handle(request):
    return web.Response(text="Bot ishlayapti!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Render porti
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    print(f"Server {port}-portda ishga tushdi.")

# --- RUNNER ---
async def main():
    logging.basicConfig(level=logging.INFO)
    # Veb serverni ishga tushirish
    asyncio.create_task(start_web_server())
    # Botni ishga tushirish
    print("Bot polling boshlandi...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

