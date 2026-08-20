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

# --- TOKENNI TO'G'RI KIRITING ---
TOKEN = "8644696840:AAE1J15_4gsDcEkzDExqOARCo38V5o3Nylo"
OWNER_ID = 7020448136 

bot = Bot(token=TOKEN)
dp = Dispatcher()
DB_FILE = "database.json"

# --- BAZA FUNKSIYALARI ---
def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try: return json.load(f)
            except: pass
    return {"users": {}, "admins": [OWNER_ID], "payment_admin": None, "channels": [], "logs": [], "promos": {"42": [], "79": [], "99": [], "299": []}}

def save_db(data):
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

def add_log(action):
    db["logs"].append(f"{datetime.now().strftime('%d.%m %H:%M')} | {action}")
    if len(db["logs"]) > 50: db["logs"].pop(0)
    save_db(db)

# --- STATE ---
class AdminStates(StatesGroup):
    bal_id = State(); bal_amount = State()
    pay_admin = State()

# --- MENYULAR ---
def main_kb(user_id):
    kb = [[KeyboardButton(text="📦 Buldrop"), KeyboardButton(text="💳 Balans")], [KeyboardButton(text="➕ Balans to'ldirish")]]
    if user_id == OWNER_ID: kb.append([KeyboardButton(text="👑 Owner Menyu")])
    if user_id in db["admins"] or user_id == OWNER_ID: kb.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# --- HANDLERLAR ---
@dp.message(Command("start"))
async def start(msg: types.Message, state: FSMContext):
    await state.clear()
    await msg.answer("👋 Assalomu alaykum! Buldrop botiga xush kelibsiz.", reply_markup=main_kb(msg.from_user.id))

@dp.message(F.text == "👑 Owner Menyu")
async def owner_menu(msg: types.Message):
    if msg.from_user.id != OWNER_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Hisob adminini qo'shish", callback_data="set_pay")],
        [InlineKeyboardButton(text="❌ Hisob adminini o'chirish", callback_data="rem_pay")],
        [InlineKeyboardButton(text="📊 Tarix (Logs)", callback_data="view_logs")]
    ])
    await msg.answer("👑 Owner paneli:", reply_markup=kb)

@dp.message(F.text == "⚙️ Admin Panel")
async def admin_menu(msg: types.Message):
    if msg.from_user.id not in db["admins"] and msg.from_user.id != OWNER_ID: return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💰 Balansni o'zgartirish", callback_data="ch_bal")]
    ])
    await msg.answer("⚙️ Admin paneli:", reply_markup=kb)

@dp.callback_query(F.data == "view_logs")
async def view_logs(call: types.CallbackQuery):
    logs = "\n".join(db["logs"]) if db["logs"] else "Tarix bo'sh"
    await call.message.answer(f"📊 Tarix:\n{logs}")

@dp.callback_query(F.data == "ch_bal")
async def ch_bal(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Foydalanuvchi ID:"); await state.set_state(AdminStates.bal_id)

@dp.message(AdminStates.bal_id)
async def get_bal_id(msg: types.Message, state: FSMContext):
    await state.update_data(target_id=msg.text); await msg.answer("Summani kiriting (masalan: 5000):")
    await state.set_state(AdminStates.bal_amount)

@dp.message(AdminStates.bal_amount)
async def set_bal(msg: types.Message, state: FSMContext):
    data = await state.get_data(); uid = data['target_id']
    if uid not in db["users"]: db["users"][uid] = {"balance": 0}
    db["users"][uid]["balance"] += int(msg.text)
    save_db(db); add_log(f"Admin {msg.from_user.id} {uid} ga {msg.text} qo'shdi")
    await msg.answer("✅ Balans yangilandi!"); await state.clear()

@dp.callback_query(F.data == "set_pay")
async def set_pay(call: types.CallbackQuery, state: FSMContext):
    await call.message.answer("Hisob admini ID:"); await state.set_state(AdminStates.pay_admin)

@dp.message(AdminStates.pay_admin)
async def save_pay(msg: types.Message, state: FSMContext):
    db["payment_admin"] = int(msg.text); save_db(db)
    await msg.answer("✅ Hisob admini tayinlandi!"); await state.clear()

@dp.callback_query(F.data == "rem_pay")
async def rem_pay(call: types.CallbackQuery):
    db["payment_admin"] = None; save_db(db); await call.message.answer("❌ Hisob admini o'chirildi!")

@dp.message(F.photo | F.document)
async def get_pay(msg: types.Message):
    add_log(f"User {msg.from_user.id} chek yubordi")
    await msg.answer("✅ Chek qabul qilindi!")
    if db.get("payment_admin"):
        try: await msg.send_copy(chat_id=db["payment_admin"])
        except: pass

# --- RENDER UCHUN WEB SERVER ---
async def handle(request): return web.Response(text="Bot is running!")

async def web_server():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', int(os.environ.get("PORT", 8080)))
    await site.start()

async def main():
    await web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
