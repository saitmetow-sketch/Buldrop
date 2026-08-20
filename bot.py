import asyncio
import os
import json
from datetime import datetime
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

TOKEN = "8644696840:AAFhsRFaMsz8XrySdMV4kAVAJ4RbITaJT34"
OWNER_ID = 7020448136

bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_FILE = "database.json"

# --- BAZA ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: pass
    return {"users": {}, "admins": [], "payment_admin": None, "channels": [], "logs": [], "balans_admin_user": None}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

def add_log(action):
    db["logs"].append(f"{datetime.now().strftime('%d.%m %H:%M')} | {action}")
    save_db(db)

# --- MENYULAR ---
def main_kb(user_id):
    kb = [[KeyboardButton(text="📦 Buldrop"), KeyboardButton(text="💳 Balans")]]
    if user_id == OWNER_ID or user_id in db["admins"]:
        kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    if user_id == OWNER_ID:
        kb.append([KeyboardButton(text="👑 Owner Menyu")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- OBUNA TEKSHIRUV ---
async def check_subs(user_id):
    for ch in db["channels"]:
        try:
            member = await bot.get_chat_member(chat_id=ch, user_id=user_id)
            if member.status == "left": return False
        except: return False
    return True

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(msg: types.Message):
    if not await check_subs(msg.from_user.id):
        await msg.answer("❌ Botdan foydalanish uchun barcha kanallarga obuna bo'ling!")
        return
    await msg.answer("👋 Xush kelibsiz!", reply_markup=main_kb(msg.from_user.id))

@dp.message(F.text == "📦 Buldrop")
async def buldrop(msg: types.Message):
    await msg.answer("📦 Buldrop mahsulotlari:\n42 ta - 5ta\n79 ta - 10ta\n99 ta - 15ta\n299 ta - 50ta")

@dp.message(F.text == "💳 Balans")
async def balans(msg: types.Message):
    uid = str(msg.from_user.id)
    bal = db["users"].get(uid, {}).get("balance", 0)
    await msg.answer(f"💰 Sizning balansingiz: {bal} so'm")

@dp.message(F.text == "➕ Balans to'ldirish")
async def pay_info(msg: types.Message):
    admin = db.get("payment_admin")
    if admin:
        await msg.answer(f"💳 Balans to'ldirish uchun ushbu admin bilan bog'laning: tg://user?id={admin}")
    else:
        await msg.answer("⚠️ Hozirda hisob admini belgilanmagan.")

# --- OWNER MENU ---
@dp.message(F.text == "👑 Owner Menyu")
async def owner_menu(msg: types.Message):
    if msg.from_user.id != OWNER_ID: return
    await msg.answer("👑 Owner paneli:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 Admin qo'shish", callback_data="add_adm")],
        [InlineKeyboardButton(text="💳 Hisob adminini qo'yish", callback_data="set_pay")],
        [InlineKeyboardButton(text="📊 Tarix (Logs)", callback_data="view_logs")]
    ]))

@dp.callback_query(F.data == "view_logs")
async def view_logs(call: types.CallbackQuery):
    await call.message.answer("\n".join(db["logs"][-20:]))

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Panel")
async def admin_menu(msg: types.Message):
    if msg.from_user.id != OWNER_ID and msg.from_user.id not in db["admins"]: return
    await msg.answer("⚙️ Admin panel:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Kanal qo'shish", callback_data="add_ch")],
        [InlineKeyboardButton(text="💰 Balans o'zgartirish", callback_data="set_bal")]
    ]))

# --- SERVER VA ASOSIY FUNKSIYA ---
async def handle(request): return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
