import asyncio
import logging
import os
import json
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8644696840:AAE1J15_4gsDCeKzDExqOARCo38V5o3Nylo"
OWNER_ID = 7020448136  # FAQAT SIZNING ID RAQAMINGIZ

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- BAZANI FAYLDA SAQLASH (JSON) ---
DB_FILE = "database.json"

def load_db():
    if os.path.exists(DB_FILE):
        with open(DB_FILE, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                data["users"] = {int(k): v for k, v in data["users"].items()}
                data["admins"] = set(int(x) for x in data["admins"])
                if data.get("payment_admin"):
                    data["payment_admin"] = int(data["payment_admin"])
                return data
            except:
                pass
    return {
        "users": {str(OWNER_ID): {"balance": 0}},
        "admins": [OWNER_ID],
        "payment_admin": None,
        "channels": [],
        "request_channels": [],
        "logs": [],
        "promos": {
            "42": [],
            "79": [],
            "99": [],
            "299": []
        }
    }

def save_db():
    data = {
        "users": {str(k): v for k, v in db["users"].items()},
        "admins": list(db["admins"]),
        "payment_admin": db["payment_admin"],
        "channels": db["channels"],
        "request_channels": db["request_channels"],
        "logs": db["logs"],
        "promos": db["promos"]
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

# --- FSM (STATE) HOLATLARI ---
class AdminStates(StatesGroup):
    waiting_for_promo = State()
    waiting_for_channel = State()
    del_channel = State()
    waiting_for_admin = State()
    del_admin = State()
    waiting_for_payment_admin = State()
    user_id_for_balance = State()
    new_balance_amount = State()

# --- KLAVIATURALAR ---
def main_menu(user_id):
    keyboard = [
        [KeyboardButton(text="📦 Buldrop"), KeyboardButton(text="💳 Balans")],
        [KeyboardButton(text="➕ Balans to'ldirish")]
    ]
    if user_id in db["admins"] or user_id == OWNER_ID:
        keyboard.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def admin_menu(user_id):
    keyboard = [
        [InlineKeyboardButton(text="➕ Promokod qo'shish", callback_data="add_promo")],
        [InlineKeyboardButton(text="💰 Balansni o'zgartirish", callback_data="change_balance")],
        [InlineKeyboardButton(text="📢 Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="🗑 Kanalni o'chirish", callback_data="del_channel")]
    ]
    # Faqat Owner uchun qo'shimcha tugmalar
    if user_id == OWNER_ID:
        keyboard.append([InlineKeyboardButton(text="👤 Admin qo'shish", callback_data="add_admin")])
        keyboard.append([InlineKeyboardButton(text="❌ Adminni o'chirish", callback_data="del_admin")])
        keyboard.append([InlineKeyboardButton(text="💳 Hisob adminini qo'shish", callback_data="set_pay_admin")])
        keyboard.append([InlineKeyboardButton(text="❌ Hisob adminini o'chirish", callback_data="rem_pay_admin")])
    
    keyboard.append([InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_home")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- START KOMANDASI ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0}
        save_db()
    
    await message.answer(
        "👋 Assalomu alaykum! Buldrop botiga xush kelibsiz.",
        reply_markup=main_menu(user_id)
    )

# --- ASOSIY MENYU ---
@dp.message(F.text == "💳 Balans")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    balance = db["users"].get(user_id, {}).get("balance", 0)
    await message.answer(f"🆔 ID: `{user_id}`\n💰 Balansingiz: {balance} so'm", parse_mode="Markdown")

@dp.message(F.text == "➕ Balans to'ldirish")
async def top_up_balance(message: types.Message):
    pay_text = "💳 **Balansni to'ldirish uchun:**\n\nKarta raqamiga pul o'tkazing va chekni hamda ID raqamingizni adminga yuboring."
    await message.answer(pay_text, parse_mode="Markdown")

@dp.message(F.text == "📦 Buldrop")
async def show_buldrop(message: types.Message):
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎁 42 – 3,500 so'm", callback_data="buy_42")],
        [InlineKeyboardButton(text="🎁 79 – 5,500 so'm", callback_data="buy_79")],
        [InlineKeyboardButton(text="🎁 99 – 8,000 so'm", callback_data="buy_99")],
        [InlineKeyboardButton(text="🎁 299 – 22,000 so'm", callback_data="buy_299")]
    ])
    await message.answer("📦 Buldrop uchun promokodlar narxlari:", reply_markup=kb)

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Panel")
async def open_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id in db["admins"] or user_id == OWNER_ID:
        await message.answer("⚙️ Admin panelga xush kelibsiz:", reply_markup=admin_menu(user_id))
    else:
        await message.answer("Sizda bu bo'limga kirish huquqi yo'q.")

@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery):
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu(callback.from_user.id))
    await callback.message.delete()

# --- HISOB ADMININI BOSHQARISH (FAQAT OWNER) ---
@dp.callback_query(F.data == "set_pay_admin")
async def set_pay_admin(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    await callback.message.answer("Hisob admini qilmoqchi bo'lgan odamning Telegram ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_payment_admin)
    await callback.answer()

@dp.message(AdminStates.waiting_for_payment_admin)
async def save_payment_admin(message: types.Message, state: FSMContext):
    try:
        new_pay_admin = int(message.text)
        db["payment_admin"] = new_pay_admin
        save_db()
        await message.answer(f"✅ Muvaffaqiyatli! ID: {new_pay_admin} endi Hisob admini etib tayinlandi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID raqam. Faqat raqam kiriting:")
        return
    await state.clear()

@dp.callback_query(F.data == "rem_pay_admin")
async def remove_pay_admin(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    db["payment_admin"] = None
    save_db()
    await callback.message.answer("❌ Hisob admini o'chirildi.")
    await callback.answer()

# --- ODDIY ADMIN QO'SHISH VA O'CHIRISH (FAQAT OWNER) ---
@dp.callback_query(F.data == "add_admin")
async def add_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    await callback.message.answer("Yangi adminning Telegram ID raqamini kiriting:")
    await state.set_state(AdminStates.waiting_for_admin)
    await callback.answer()

@dp.message(AdminStates.waiting_for_admin)
async def save_new_admin(message: types.Message, state: FSMContext):
    try:
        aid = int(message.text)
        db["admins"].add(aid)
        save_db()
        await message.answer(f"✅ ID: {aid} adminlar ro'yxatiga qo'shildi.")
    except ValueError:
        await message.answer("❌ Xato format. Faqat raqam kiriting:")
        return
    await state.clear()

@dp.callback_query(F.data == "del_admin")
async def del_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    await callback.message.answer(f"O'chirmoqchi bo'lgan admin ID raqamini kiriting (Adminlar: {list(db['admins'])}):")
    await state.set_state(AdminStates.del_admin)
    await callback.answer()

@dp.message(AdminStates.del_admin)
async def remove_admin(message: types.Message, state: FSMContext):
    try:
        aid = int(message.text)
        if aid == OWNER_ID:
            await message.answer("❌ Owner'ni o'chirib bo'lmaydi!")
            return
        if aid in db["admins"]:
            db["admins"].remove(aid)
            save_db()
            await message.answer(f"✅ ID: {aid} adminlikdan olib tashlandi.")
        else:
            await message.answer("❌ Bu ID ro'yxatda yo'q.")
    except ValueError:
        await message.answer("❌ Xato format.")
        return
    await state.clear()

# --- KANALLarni BOSHQARISH (ADMINLAR VA OWNER UCHUN) ---
@dp.callback_query(F.data == "add_channel")
async def add_channel_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in db["admins"] and user_id != OWNER_ID:
        return await callback.answer("Sizda bu huquq yo'q!", show_alert=True)
    await callback.message.answer("Kanal username yoki ID raqamini yuboring (masalan: @kanal_nomi):")
    await state.set_state(AdminStates.waiting_for_channel)
    await callback.answer()

@dp.message(AdminStates.waiting_for_channel)
async def save_channel(message: types.Message, state: FSMContext):
    channel = message.text.strip()
    if channel not in db["channels"]:
        db["channels"].append(channel)
        save_db()
        await message.answer(f"✅ Kanal qo'shildi: {channel}")
    else:
        await message.answer("⚠️ Bu kanal allaqachon mavjud.")
    await state.clear()

@dp.callback_query(F.data == "del_channel")
async def del_channel_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in db["admins"] and user_id != OWNER_ID:
        return await callback.answer("Sizda bu huquq yo'q!", show_alert=True)
    await callback.message.answer(f"O'chirmoqchi bo'lgan kanalni yuboring (Hozirgi kanallar: {db['channels']}):")
    await state.set_state(AdminStates.del_channel)
    await callback.answer()

@dp.message(AdminStates.del_channel)
async def remove_channel(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    if ch in db["channels"]:
        db["channels"].remove(ch)
        save_db()
        await message.answer(f"✅ Kanal o'chirildi: {ch}")
    else:
        await message.answer("❌ Bunday kanal topilmadi.")
    await state.clear()

# --- CHEK KELGANDA FAQAT OWNER VA HISOB ADMINIGA YUBORISH ---
@dp.message(F.photo | F.document)
async def catch_payment_proof(message: types.Message):
    user_id = message.from_user.id
    if user_id in db["admins"] or user_id == OWNER_ID:
        return # Adminlarning o'zi yuborgan bo'lsa e'tibor bermaymiz

    caption = f"🔔 **Yangi to'lov cheki keldi!**\n👤 Foydalanuvchi: [Profil](tg://user?id={user_id})\n🆔 ID: `{user_id}`"
    
    # Ownerga yuborish
    try:
        await message.send_copy(chat_id=OWNER_ID, caption=caption, parse_mode="Markdown")
    except:
        pass

    # Hisob adminiga yuborish (agar tayinlangan bo'lsa)
    pay_admin = db.get("payment_admin")
    if pay_admin and pay_admin != OWNER_ID:
        try:
            await message.send_copy(chat_id=pay_admin, caption=caption, parse_mode="Markdown")
        except:
            pass

    await message.answer("✅ Chekingiz qabul qilindi! Hisob admini tekshirib, balansingizni to'ldirib beradi.")

# Botni ishga tushirish
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
