import asyncio
import logging
import os
import json
from datetime import datetime
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8644696840:AAE1J15_4gsDcEkzDExqOARCo38V5o3Nylo"
OWNER_ID = 7020448136  # SIZNING ID RAQAMINGIZ

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
        "logs": [], # Barcha tarixlar shu yerda saqlanadi
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

# Tarixga yozish funksiyasi
def add_log(text):
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_msg = f"[{current_time}] {text}"
    db["logs"].append(log_msg)
    # Tarix juda ko'p 100 tadan oshib ketmasa uchun oxirgi 100 tasini saqlaymiz
    if len(db["logs"]) > 100:
        db["logs"].pop(0)
    save_db()

# --- FSM (STATE) ---
class AdminStates(StatesGroup):
    waiting_for_promo_code = State()
    waiting_for_channel = State()
    del_channel = State()
    waiting_for_admin = State()
    del_admin = State()
    waiting_for_payment_admin = State()
    change_balance_id = State()
    change_balance_amount = State()

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
        [KeyboardButton(text="➕ Balans to'ldirish") ]
    ]
    if user_id == OWNER_ID:
        keyboard.append([KeyboardButton(text="👑 Owner Menyu")])
        keyboard.append([KeyboardButton(text="⚙️ Admin Panel")])
    elif user_id in db["admins"]:
        keyboard.append([KeyboardButton(text="⚙️ Admin Panel")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# Owner menyusi (Faqat ownerga ko'rinadi)
def owner_menu():
    keyboard = [
        [InlineKeyboardButton(text="💳 Hisob adminini qo'shish", callback_data="set_pay_admin")],
        [InlineKeyboardButton(text="❌ Hisob adminini o'chirish", callback_data="rem_pay_admin")],
        [InlineKeyboardButton(text="📊 Tarix va Ma'lumotlar", callback_data="view_logs")],
        [InlineKeyboardButton(text="👤 Admin qo'shish", callback_data="add_admin")],
        [InlineKeyboardButton(text="❌ Adminni o'chirish", callback_data="del_admin")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# Oddiy admin menyusi (Ownerga ham, oddiy adminlarga ham chiqadi, lekin hisob admini yo'q)
def admin_menu():
    keyboard = [
        [InlineKeyboardButton(text="➕ Promokod qo'shish", callback_data="add_promo")],
        [InlineKeyboardButton(text="💰 Balansni o'zgartirish", callback_data="change_balance")],
        [InlineKeyboardButton(text="📢 Kanal qo'shish", callback_data="add_channel")],
        [InlineKeyboardButton(text="🗑 Kanalni o'chirish", callback_data="del_channel")],
        [InlineKeyboardButton(text="🔙 Asosiy menyu", callback_data="back_home")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = message.from_user.id
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0}
        save_db()
    
    await message.answer(
        "👋 Assalomu alaykum! Buldrop botiga xush kelibsiz.",
        reply_markup=main_menu(user_id)
    )

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

@dp.callback_query(F.data.startswith("buy_"))
async def buy_promo(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    p_type = callback.data.split("_")[1]
    price = PRICES[p_type]
    
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0}
        save_db()
        
    user_balance = db["users"][user_id]["balance"]
    
    if user_balance < price:
        return await callback.answer(f"❌ Balansingizda mablag' yetarli emas! Kerak: {price} so'm", show_alert=True)
    
    if not db["promos"].get(p_type) or len(db["promos"][p_type]) == 0:
        return await callback.answer("❌ Kechirasiz, hozirda bu turkumda promokodlar qolmagan!", show_alert=True)
    
    promo_code = db["promos"][p_type].pop(0)
    db["users"][user_id]["balance"] -= price
    save_db()
    
    # Tarixga yozish
    add_log(f"Foydalanuvchi ({user_id}) {p_type} turkumidagi promokodni sotib oldi.")

    await callback.message.answer(
        f"✅ **Tabriklaymiz! Muvaffaqiyatli xarid qildingiz.**\n\n"
        f"📦 Turkum: **{p_type}**\n"
        f"🔑 Promokodingiz:\n`{promo_code}`\n\n"
        f"💰 Qolgan balansingiz: {db['users'][user_id]['balance']} so'm",
        parse_mode="Markdown"
    )
    await callback.answer()

# --- OWNER MENYU ---
@dp.message(F.text == "👑 Owner Menyu")
async def open_owner_menu(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return await message.answer("Sizda bu bo'limga kirish huquqi yo'q!")
    await message.answer("👑 Owner boshqaruv paneliga xush kelibsiz:", reply_markup=owner_menu())

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Panel")
async def open_admin(message: types.Message):
    user_id = message.from_user.id
    if user_id in db["admins"] or user_id == OWNER_ID:
        await message.answer("⚙️ Admin panelga xush kelibsiz:", reply_markup=admin_menu())
    else:
        await message.answer("Sizda bu bo'limga kirish huquqi yo'q.")

@dp.callback_query(F.data == "back_home")
async def back_home(callback: types.CallbackQuery):
    await callback.message.answer("Asosiy menyu:", reply_markup=main_menu(callback.from_user.id))
    await callback.message.delete()

# --- TARIX VA MA'LUMOTLARNI KO'RISH ---
@dp.callback_query(F.data == "view_logs")
async def view_logs(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    
    logs = db.get("logs", [])
    if not logs:
        return await callback.answer("Hozircha tarix bo'sh.", show_alert=True)
    
    # Oxirgi 15 ta harakatni ko'rsatamiz
    last_logs = "\n".join(logs[-15:])
    text = f"📊 **Oxirgi harakatlar tarixi:**\n\n{last_logs}"
    
    if len(text) > 4000:
        text = text[:4000]
        
    await callback.message.answer(text, parse_mode="Markdown")
    await callback.answer()

# --- PROMOKOD QO'SHISH ---
@dp.callback_query(F.data == "add_promo")
async def add_promo_start(callback: types.CallbackQuery, state: FSMContext):
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
    await callback.message.answer(f"📦 **{p_type}** turkumi uchun promokod(lar)ni yuboring:")
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
    add_log(f"Admin ({message.from_user.id}) {p_type} turkumiga {added_count} ta promokod qo'shdi.")
    await message.answer(f"✅ **{p_type}** turkumiga {added_count} ta promokod qo'shildi.")
    await state.clear()

# --- HISOB ADMININI BOSHQARISH ---
@dp.callback_query(F.data == "set_pay_admin")
async def set_pay_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    await callback.message.answer("💳 Hisob admini qilmoqchi bo'lgan foydalanuvchining **Telegram ID raqamini** yuboring:")
    await state.set_state(AdminStates.waiting_for_payment_admin)
    await callback.answer()

@dp.message(AdminStates.waiting_for_payment_admin)
async def save_payment_admin(message: types.Message, state: FSMContext):
    try:
        new_pay_admin = int(message.text.strip())
        db["payment_admin"] = new_pay_admin
        save_db()
        add_log(f"Owner hisob adminini o'zgartirdi: ID ({new_pay_admin})")
        await message.answer(f"✅ Muvaffaqiyatli! ID: `{new_pay_admin}` hisob admini etib tayinlandi.", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Xato! Faqat raqamdan iborat Telegram ID yuboring.")
    await state.clear()

@dp.callback_query(F.data == "rem_pay_admin")
async def remove_payment_admin(callback: types.CallbackQuery):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    db["payment_admin"] = None
    save_db()
    add_log("Owner hisob adminini o'chirdi.")
    await callback.message.answer("❌ Hisob admini o'chirildi.")
    await callback.answer()

# --- ADMIN QO'SHISH / O'CHIRISH ---
@dp.callback_query(F.data == "add_admin")
async def add_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    await callback.message.answer("➕ Yangi adminning Telegram ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_admin)
    await callback.answer()

@dp.message(AdminStates.waiting_for_admin)
async def save_admin(message: types.Message, state: FSMContext):
    try:
        new_admin = int(message.text.strip())
        db["admins"].add(new_admin)
        save_db()
        add_log(f"Yangi admin qo'shildi: ID ({new_admin})")
        await message.answer(f"✅ ID: `{new_admin}` adminlar safiga qo'shildi.", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Xato ID.")
    await state.clear()

@dp.callback_query(F.data == "del_admin")
async def del_admin_start(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != OWNER_ID:
        return await callback.answer("Faqat Owner uchun!", show_alert=True)
    await callback.message.answer(f"❌ O'chirmoqchi bo'lgan admin ID raqamini yuboring\n(Hozirgi adminlar: {list(db['admins'])}):")
    await state.set_state(AdminStates.del_admin)
    await callback.answer()

@dp.message(AdminStates.del_admin)
async def remove_admin(message: types.Message, state: FSMContext):
    try:
        rem_admin = int(message.text.strip())
        if rem_admin == OWNER_ID:
            await message.answer("⚠️ Owner'ni o'chirib bo'lmaydi!")
        elif rem_admin in db["admins"]:
            db["admins"].remove(rem_admin)
            save_db()
            add_log(f"Admin o'chirildi: ID ({rem_admin})")
            await message.answer(f"✅ ID: `{rem_admin}` adminlikdan olib tashlandi.", parse_mode="Markdown")
        else:
            await message.answer("❌ Bunday admin topilmadi.")
    except ValueError:
        await message.answer("❌ Xato ID.")
    await state.clear()

# --- BALANSNI O'ZGARTIRISH ---
@dp.callback_query(F.data == "change_balance")
async def change_bal_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("👤 Balansini o'zgartirmoqchi bo'lgan foydalanuvchining **Telegram ID raqamini** yuboring:")
    await state.set_state(AdminStates.change_balance_id)
    await callback.answer()

@dp.message(AdminStates.change_balance_id)
async def change_bal_get_id(message: types.Message, state: FSMContext):
    try:
        target_id = int(message.text.strip())
        await state.update_data(target_id=target_id)
        await message.answer("💰 Foydalanuvchining balansiga qo'shiladigan yoki ayiriladigan summani kiriting:\n(Masalan: `5000` yoki `-2000`)")
        await state.set_state(AdminStates.change_balance_amount)
    except ValueError:
        await message.answer("❌ Xato ID raqam.")
        await state.clear()

@dp.message(AdminStates.change_balance_amount)
async def change_bal_finish(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        data = await state.get_data()
        target_id = data.get("target_id")
        
        if target_id not in db["users"]:
            db["users"][target_id] = {"balance": 0}
            
        db["users"][target_id]["balance"] += amount
        save_db()
        add_log(f"Admin ({message.from_user.id}) foydalanuvchi ({target_id}) balansini {amount} so'mga o'zgartirdi.")
        
        await message.answer(f"✅ Muvaffaqiyatli! ID: `{target_id}` ning balansi {amount} so'mga o'zgartirildi. Yangi balans: {db['users'][target_id]['balance']} so'm", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting.")
    await state.clear()

# --- KANALLARNI BOSHQARISH ---
@dp.callback_query(F.data == "add_channel")
async def add_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer("Kanal username yoki ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_channel)
    await callback.answer()

@dp.message(AdminStates.waiting_for_channel)
async def save_channel(message: types.Message, state: FSMContext):
    channel = message.text.strip()
    if channel not in db["channels"]:
        db["channels"].append(channel)
        save_db()
        add_log(f"Kanal qo'shildi: {channel}")
        await message.answer(f"✅ Kanal qo'shildi: {channel}")
    else:
        await message.answer("⚠️ Bu kanal allaqachon mavjud.")
    await state.clear()

@dp.callback_query(F.data == "del_channel")
async def del_channel_start(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.answer(f"O'chirmoqchi bo'lgan kanalni yuboring (Hozirgi kanallar: {db['channels']}):")
    await state.set_state(AdminStates.del_channel)
    await callback.answer()

@dp.message(AdminStates.del_channel)
async def remove_channel(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    if ch in db["channels"]:
        db["channels"].remove(ch)
        save_db()
        add_log(f"Kanal o'chirildi: {ch}")
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

    add_log(f"Foydalanuvchi ({user_id}) to'lov chekini yubordi.")

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

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
