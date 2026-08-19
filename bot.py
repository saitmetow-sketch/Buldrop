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
TOKEN = "8644696840:AAGMNi0SgF27zbuJDvYM6Y6HsAIFV2GaaCk"
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
    waiting_for_promo_type = State()
    waiting_for_promo_code = State()
    waiting_for_channel = State()
    del_channel = State()
    waiting_for_admin = State()
    del_admin = State()
    waiting_for_payment_admin = State()

# Narxlar Lug'ati
PRICES = {
    "42": 3500,
    "79": 5500,
    "99": 8000,
    "299": 22000
}

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
        [InlineKeyboardButton(text=f"🎁 42 – {PRICES['42']} so'm", callback_data="buy_42")],
        [InlineKeyboardButton(text=f"🎁 79 – {PRICES['79']} so'm", callback_data="buy_79")],
        [InlineKeyboardButton(text=f"🎁 99 – {PRICES['99']} so'm", callback_data="buy_99")],
        [InlineKeyboardButton(text=f"🎁 299 – {PRICES['299']} so'm", callback_data="buy_299")]
    ])
    await message.answer("📦 Buldrop uchun promokodlar narxlari:", reply_markup=kb)

# --- PROMOKOD SOTIB OLISH (AVTOMATIK O'CHIRISH VA YUBORISH) ---
@dp.callback_query(F.data.startswith("buy_"))
async def buy_promo(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    p_type = callback.data.split("_")[1]
    price = PRICES[p_type]
    
    # Foydalanuvchi bazada borligini tekshirish
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0}
        save_db()
        
    user_balance = db["users"][user_id]["balance"]
    
    # Balans yetarliligini tekshirish
    if user_balance < price:
        return await callback.answer(f"❌ Balansingizda mablag' yetarli emas! Kerak: {price} so'm", show_alert=True)
    
    # Zaxirada promokod borligini tekshirish
    if not db["promos"].get(p_type) or len(db["promos"][p_type]) == 0:
        return await callback.answer("❌ Kechirasiz, hozirda bu turkumda promokodlar qolmagan!", show_alert=True)
    
    # Promokodni olish va bazadan o'chirish
    promo_code = db["promos"][p_type].pop(0) # Ro'yxat boshidagi bitta promokodni sug'urib oladi
    db["users"][user_id]["balance"] -= price # Balansdan pulni ayiradi
    save_db()
    
    # Foydalanuvchiga yuborish
    await callback.message.answer(
        f"✅ **Tabriklaymiz! Muvaffaqiyatli xarid qildingiz.**\n\n"
        f"📦 Turkum: **{p_type}**\n"
        f"🔑 Promokodingiz:\n`{promo_code}`\n\n"
        f"💰 Qolgan balansingiz: {db['users'][user_id]['balance']} so'm",
        parse_mode="Markdown"
    )
    await callback.answer()

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

# --- PROMOKOD QO'SHISH ---
@dp.callback_query(F.data == "add_promo")
async def add_promo_start(callback: types.CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    if user_id not in db["admins"] and user_id != OWNER_ID:
        return await callback.answer("Sizda bu huquq yo'q!", show_alert=True)
    
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="42", callback_data="p_42"), InlineKeyboardButton(text="79", callback_data="p_79")],
        [InlineKeyboardButton(text="99", callback_data="p_99"), InlineKeyboardButton(text="299", callback_data="p_299")]
    ])
    await callback.message.answer("Qaysi turkumga promokod qo'shmoqchisiz?", reply_markup=kb)
    await callback.answer()

@dp.callback_query(F.data.startswith("p_"))
async def select_promo_type(callback: types.CallbackQuery, state: FSMContext):
    p_type = callback.data.split("_")[1]
    await state.update_data(promo_type=p_type)
    await callback.message.answer(f"📦 **{p_type}** turkumi uchun promokod(lar)ni yuboring:\n(Bir nechta bo'lsa har birini yangi qatordan yozib yuboring)")
    await state.set_state(AdminStates.waiting_for_promo_code)
    await callback.answer()

@dp.message(AdminStates.waiting_for_promo_code)
async def save_promo_codes(message: types.Message, state: FSMContext):
    data = await state.get_data()
    p_type = data.get("promo_type")
    
    codes = message.text.strip().split("\n")
    added_count = 0
    
    for code in codes:
        code = code.strip()
        if code and code not in db["promos"][p_type]:
            db["promos"][p_type].append(code)
            added_count += 1
            
    save_db()
    await message.answer(f"✅ Muvaffaqiyatli! **{p_type}** turkumiga {added_count} ta yangi promokod qo'shildi. (Jami zaxira: {len(db['promos'][p_type])} ta)")
    await state.clear()

# --- KANALLARNI BOSHQARISH ---
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

# --- CHEK KELGANDA ---
@dp.message(F.photo | F.document)
async def catch_payment_proof(message: types.Message):
    user_id = message.from_user.id
    if user_id in db["admins"] or user_id == OWNER_ID:
        return 

    caption = f"🔔 **Yangi to'lov cheki keldi!**\n👤 Foydalanuvchi: [Profil](tg://user?id={user_id})\n🆔 ID: `{user_id}`"
    
    try:
        await message.send_copy(chat_id=OWNER_ID, caption=caption, parse_mode="Markdown")
    except:
        pass

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
