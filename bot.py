import asyncio
import logging
import os
import json
import aiohttp
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8644696840:AAFhsRFaMsz8XrySdMV4kAVAJ4RbITaJT34"
OWNER_ID = 7020448136  # Sizning ID raqamingiz

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
                return data
            except:
                pass
    return {
        "users": {OWNER_ID: {"balance": 0}},
        "admins": {OWNER_ID},
        "req_channels": [],     # So'rovli obuna kanallari
        "sub_channels": [],     # Majburiy obuna kanallari
        "payment_admins": [],   # Hisob adminlari ID lari
        "logs": [],             # Barcha harakatlar tarixi
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
        "req_channels": db["req_channels"],
        "sub_channels": db["sub_channels"],
        "payment_admins": db["payment_admins"],
        "logs": db["logs"][-100:], # Oxirgi 100 ta tarix saqlanadi
        "promos": db["promos"]
    }
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

db = load_db()

def add_log(text: str):
    db["logs"].append(text)
    save_db()

# --- FSM (STATE) HOLATLARI ---
class AdminStates(StatesGroup):
    waiting_for_promo = State()
    waiting_for_sub_ch = State()
    del_sub_ch = State()
    waiting_for_req_ch = State()
    del_req_ch = State()
    waiting_for_admin = State()
    del_admin = State()
    waiting_for_pay_admin = State()
    del_pay_admin = State()
    user_id_for_balance = State()
    new_balance_amount = State()
    broadcast_text = State()

# --- OBUNANI TEKSHIRISH ---
async def check_subscription(user_id: int) -> bool:
    all_channels = db["sub_channels"] + db["req_channels"]
    if not all_channels:
        return True
    for channel in all_channels:
        try:
            member = await bot.get_chat_member(chat_id=channel, user_id=user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            pass
    return True

async def get_sub_keyboard():
    keyboard = []
    all_channels = db["sub_channels"] + db["req_channels"]
    for ch in all_channels:
        try:
            chat = await bot.get_chat(ch)
            keyboard.append([InlineKeyboardButton(text=f"📢 {chat.title}", url=f"https://t.me/{ch.lstrip('@')}")])
        except:
            keyboard.append([InlineKeyboardButton(text=f"📢 Kanal", url=f"https://t.me/{ch.lstrip('@')}")])
    keyboard.append([InlineKeyboardButton(text="✅ Obunani tekshirish", callback_data="check_sub")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

# --- MENYULAR ---
def get_main_menu(user_id):
    keyboard = [
        [KeyboardButton(text="📦 Bulldrop")],
        [KeyboardButton(text="💳 Balans"), KeyboardButton(text="➕ Balans to'ldirish")]
    ]
    if user_id in db["admins"] or user_id == OWNER_ID:
        keyboard.append([KeyboardButton(text="⚙️ Admin Panel")])
    if user_id == OWNER_ID:
        keyboard.append([KeyboardButton(text="👑 Owner Panel")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

# --- START ---
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    if user_id not in db["users"]:
        db["users"][user_id] = {"balance": 0}
        save_db()

    if not await check_subscription(user_id):
        await message.answer("⚠️ **Botdan foydalanish uchun quyidagi kanallarga obuna bo'ling:**", reply_markup=await get_sub_keyboard(), parse_mode="Markdown")
        return

    await message.answer("🏠 **Bosh sahifa:**\nQuyidagi bo'limlardan birini tanlang:", reply_markup=get_main_menu(user_id), parse_mode="Markdown")

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    if await check_subscription(user_id):
        await callback.message.delete()
        await callback.message.answer("🏠 **Bosh sahifa:**", reply_markup=get_main_menu(user_id), parse_mode="Markdown")
    else:
        await callback.answer("❌ Hali hamma kanalga obuna bo'lmadingiz!", show_alert=True)

@dp.message(F.text == "🏠 Bosh menyu")
async def back_to_menu(message: types.Message):
    user_id = message.from_user.id
    if not await check_subscription(user_id):
        await message.answer("⚠️ Avval kanallarga obuna bo'ling!", reply_markup=await get_sub_keyboard())
        return
    await message.answer("🏠 **Bosh sahifa:**", reply_markup=get_main_menu(user_id), parse_mode="Markdown")

# --- BULLDROP BO'LIMI ---
@dp.message(F.text == "📦 Bulldrop")
async def bulldrop_menu(message: types.Message):
    if not await check_subscription(message.from_user.id):
        await message.answer("⚠️ Avval kanallarga obuna bo'ling!", reply_markup=await get_sub_keyboard())
        return

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
        "Videoda botdan kod olinishi, nusxalanib darhol saytga qo'yilishi va faollashtirilishi kesilmasdan ko'rinishi shart."
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
    user = callback.from_user
    
    prices = {"42": 3500, "79": 5500, "99": 8000, "299": 22000}
    price = prices[code_type]
    
    if db["users"][user_id]["balance"] < price:
        await callback.answer(f"❌ Balansingiz yetarli emas! Sizda: {db['users'][user_id]['balance']} so'm", show_alert=True)
        return
        
    if not db["promos"][code_type]:
        await callback.answer("❌ Afsuski, bu turdagi promokodlar hozircha qolmagan!", show_alert=True)
        return
        
    db["users"][user_id]["balance"] -= price
    promo_code = db["promos"][code_type].pop(0) 
    save_db()
    
    add_log(f"🛒 Xarid: {user.full_name} ({user_id}) - {code_type} tur ({price} so'm). Kod: {promo_code}")

    await callback.message.delete()
    await callback.message.answer(f"🎉 **Tabriklaymiz! Xarid muvaffaqiyatli.**\n\nSizning promokodingiz:\n`{promo_code}`", parse_mode="Markdown")
    await callback.answer()

# --- BALANS VA HISOB ADMINI ---
@dp.message(F.text == "💳 Balans")
async def show_balance(message: types.Message):
    user_id = message.from_user.id
    bal = db["users"].get(user_id, {}).get("balance", 0)
    await message.answer(f"🆔 ID: `{user_id}`\n💰 Balansingiz: **{bal} so'm**", parse_mode="Markdown")

@dp.message(F.text == "➕ Balans to'ldirish")
async def top_up_balance(message: types.Message):
    if not db["payment_admins"]:
        await message.answer("💳 Balansni to'ldirish uchun hozircha hisob admini tayinlanmagan.")
        return
    
    pay_links = []
    for padm in db["payment_admins"]:
        try:
            user_info = await bot.get_chat(padm)
            username = user_info.username
            if username:
                pay_links.append(f"👤 Hisob admini: @{username}")
            else:
                pay_links.append(f"👤 Hisob admini: [Foydalanuvchi](tg://user?id={padm})")
        except:
            pay_links.append(f"👤 Hisob admini ID: `{padm}`")
            
    text = "💳 **Balansni to'ldirish uchun quyidagi hisob adminiga murojaat qiling va chekni yuboring:**\n\n" + "\n".join(pay_links)
    await message.answer(text, parse_mode="Markdown")

# --- ADMIN PANEL ---
@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(message: types.Message):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    keyboard = [
        [KeyboardButton(text="➕ Promokod qo'shish"), KeyboardButton(text="📊 Statistika")],
        [KeyboardButton(text="➕ Majburiy kanal"), KeyboardButton(text="➖ Majburiy kanalni o'chirish")],
        [KeyboardButton(text="➕ So'rovli kanal"), KeyboardButton(text="➖ So'rovli kanalni o'chirish")],
        [KeyboardButton(text="📢 Xabar yuborish (Reklama)")],
        [KeyboardButton(text="💰 Foydalanuvchi balansini o'zgartirish")],
        [KeyboardButton(text="🏠 Bosh menyu")]
    ]
    await message.answer("⚙️ **Admin Boshqaruv Paneli:**", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True), parse_mode="Markdown")

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    total_users = len(db["users"])
    p_counts = "\n".join([f"• {k}-tur: {len(v)} ta" for k, v in db["promos"].items()])
    await message.answer(f"📊 **Statistika:**\n\n👥 Foydalanuvchilar: {total_users} ta\n\n📦 **Qolgan promokodlar:**\n{p_counts}", parse_mode="Markdown")

# --- OWNER PANEL ---
@dp.message(F.text == "👑 Owner Panel")
async def owner_panel(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    keyboard = [
        [KeyboardButton(text="➕ Admin qo'shish"), KeyboardButton(text="➖ Adminni o'chirish")],
        [KeyboardButton(text="➕ Hisob admini qo'shish"), KeyboardButton(text="➖ Hisob adminini o'chirish")],
        [KeyboardButton(text="📜 Tarix (Logs) bo'limi")],
        [KeyboardButton(text="🏠 Bosh menyu")]
    ]
    await message.answer("👑 **Owner Boshqaruv Paneli:**", reply_markup=ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True), parse_mode="Markdown")

# --- TARIX (LOGS) BO'LIMI ---
@dp.message(F.text == "📜 Tarix (Logs) bo'limi")
async def show_logs(message: types.Message):
    if message.from_user.id != OWNER_ID:
        return
    if not db["logs"]:
        await message.answer("📜 Hozircha tarix bo'sh.")
        return
    logs_text = "📜 **Oxirgi harakatlar tarixi:**\n\n" + "\n".join(db["logs"][-30:])
    if len(logs_text) > 4000:
        logs_text = logs_text[-4000:]
    await message.answer(logs_text, parse_mode="Markdown")

# --- REKLAMA (XABAR YUBORISH) ---
@dp.message(F.text == "📢 Xabar yuborish (Reklama)")
async def broadcast_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    await message.answer("📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni (matn, rasm yoki video) yuboring:")
    await state.set_state(AdminStates.broadcast_text)

@dp.message(AdminStates.broadcast_text)
async def broadcast_send(message: types.Message, state: FSMContext):
    users = list(db["users"].keys())
    success = 0
    fail = 0
    await message.answer("⏳ Xabar yuborish boshlandi...")
    for uid in users:
        try:
            await message.send_copy(chat_id=uid)
            success += 1
            await asyncio.sleep(0.05)
        except:
            fail += 1
    add_log(f"📢 Reklama yuborildi: Muvaffaqiyatli {success}, Xato {fail}")
    await message.answer(f"✅ Xabar yuborish yakunlandi!\n\nMuvaffaqiyatli: {success} ta\nYetib bormadi: {fail} ta")
    await state.clear()

# --- PROMOKOD QO'SHISH ---
@dp.message(F.text == "➕ Promokod qo'shish")
async def add_promo_menu(message: types.Message, state: FSMContext):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    keyboard = [
        [InlineKeyboardButton(text="42", callback_data="add_p_42"), InlineKeyboardButton(text="79", callback_data="add_p_79")],
        [InlineKeyboardButton(text="99", callback_data="add_p_99"), InlineKeyboardButton(text="299", callback_data="add_p_299")]
    ]
    await message.answer("Qaysi turdagi promokod qo'shmoqchisiz?", reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard))

@dp.callback_query(F.data.startswith("add_p_"))
async def add_promo_type(callback: types.CallbackQuery, state: FSMContext):
    code_type = callback.data.split("_")[2]
    await state.update_data(code_type=code_type)
    await callback.message.answer(f"OK! `{code_type}` turidagi promokodlarni yuboring (Har birini yangi qatordan yuboring):", parse_mode="Markdown")
    await state.set_state(AdminStates.waiting_for_promo)
    await callback.answer()

@dp.message(AdminStates.waiting_for_promo)
async def save_promo_handler(message: types.Message, state: FSMContext):
    data = await state.get_data()
    code_type = data["code_type"]
    admin = message.from_user
    
    codes = message.text.split("\n")
    added_count = 0
    for code in codes:
        code = code.strip()
        if code:
            db["promos"][code_type].append(code)
            added_count += 1
            
    save_db()
    add_log(f"➕ Admin {admin.full_name} ({admin.id}) {code_type} turiga {added_count} ta promokod qo'shdi.")

    await message.answer(f"✅ Muvaffaqiyatli {added_count} ta promokod `{code_type}` turiga qo'shildi!", parse_mode="Markdown")
    await state.clear()

# --- KANALLarni BOSHQARISH (Majburiy va So'rovli) ---
@dp.message(F.text == "➕ Majburiy kanal")
async def add_sub_ch_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    await message.answer("Majburiy kanal usernamesini yuboring (Masalan: `@kanal_username`):")
    await state.set_state(AdminStates.waiting_for_sub_ch)

@dp.message(AdminStates.waiting_for_sub_ch)
async def save_sub_ch(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    if ch not in db["sub_channels"]:
        db["sub_channels"].append(ch)
        save_db()
        add_log(f"📢 Majburiy kanal qo'shildi: {ch}")
        await message.answer(f"✅ Majburiy kanal {ch} qo'shildi!")
    else:
        await message.answer("⚠️ Bu kanal allaqachon mavjud.")
    await state.clear()

@dp.message(F.text == "➖ Majburiy kanalni o'chirish")
async def del_sub_ch_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    if not db["sub_channels"]:
        await message.answer("Hozircha majburiy kanallar yo'q.")
        return
    text = "O'chirmoqchi bo'lgan majburiy kanalni tanlang:\n" + "\n".join(db["sub_channels"])
    await message.answer(text + "\n\nKanal usernamesini yuboring:")
    await state.set_state(AdminStates.del_sub_ch)

@dp.message(AdminStates.del_sub_ch)
async def remove_sub_ch(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    if ch in db["sub_channels"]:
        db["sub_channels"].remove(ch)
        save_db()
        add_log(f"❌ Majburiy kanal o'chirildi: {ch}")
        await message.answer(f"❌ Kanal o'chirildi!")
    else:
        await message.answer("❌ Topilmadi.")
    await state.clear()

@dp.message(F.text == "➕ So'rovli kanal")
async def add_req_ch_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    await message.answer("So'rovli kanal usernamesini yuboring (Masalan: `@kanal_username`):")
    await state.set_state(AdminStates.waiting_for_req_ch)

@dp.message(AdminStates.waiting_for_req_ch)
async def save_req_ch(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    if ch not in db["req_channels"]:
        db["req_channels"].append(ch)
        save_db()
        add_log(f"📢 So'rovli kanal qo'shildi: {ch}")
        await message.answer(f"✅ So'rovli kanal {ch} qo'shildi!")
    else:
        await message.answer("⚠️ Bu kanal allaqachon mavjud.")
    await state.clear()

@dp.message(F.text == "➖ So'rovli kanalni o'chirish")
async def del_req_ch_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    if not db["req_channels"]:
        await message.answer("Hozircha so'rovli kanallar yo'q.")
        return
    text = "O'chirmoqchi bo'lgan so'rovli kanalni tanlang:\n" + "\n".join(db["req_channels"])
    await message.answer(text + "\n\nKanal usernamesini yuboring:")
    await state.set_state(AdminStates.del_req_ch)

@dp.message(AdminStates.del_req_ch)
async def remove_req_ch(message: types.Message, state: FSMContext):
    ch = message.text.strip()
    if ch in db["req_channels"]:
        db["req_channels"].remove(ch)
        save_db()
        add_log(f"❌ So'rovli kanal o'chirildi: {ch}")
        await message.answer(f"❌ Kanal o'chirildi!")
    else:
        await message.answer("❌ Topilmadi.")
    await state.clear()

# --- ADMINLARNI BOSHQARISH (Owner) ---
@dp.message(F.text == "➕ Admin qo'shish")
async def add_admin_start(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("Yangi adminning Telegram ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_admin)

@dp.message(AdminStates.waiting_for_admin)
async def save_admin(message: types.Message, state: FSMContext):
    try:
        new_id = int(message.text.strip())
        db["admins"].add(new_id)
        save_db()
        add_log(f"👑 Yangi admin qo'shildi ID: {new_id}")
        await message.answer(f"👑 ID `{new_id}` adminlar safiga qo'shildi!", parse_mode="Markdown")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID!")
    await state.clear()

@dp.message(F.text == "➖ Adminni o'chirish")
async def del_admin_start(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    admins_list = "\n".join([str(a) for a in db["admins"] if a != OWNER_ID])
    if not admins_list:
        await message.answer("Boshqa adminlar yo'q.")
        return
    await message.answer(f"Mavjud adminlar:\n{admins_list}\n\nO'chirmoqchi bo'lgan admin ID sini yuboring:")
    await state.set_state(AdminStates.del_admin)

@dp.message(AdminStates.del_admin)
async def remove_admin(message: types.Message, state: FSMContext):
    try:
        adm_id = int(message.text.strip())
        if adm_id == OWNER_ID:
            await message.answer("O'zini o'chirib bo'lmaydi!")
        elif adm_id in db["admins"]:
            db["admins"].remove(adm_id)
            save_db()
            add_log(f"❌ Admin o'chirildi ID: {adm_id}")
            await message.answer("❌ Admin o'chirildi.")
        else:
            await message.answer("Topilmadi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID!")
    await state.clear()

# --- HISOB ADMINLARINI BOSHQARISH (Owner) ---
@dp.message(F.text == "➕ Hisob admini qo'shish")
async def add_pay_admin_start(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    await message.answer("Yangi hisob adminining (Balans to'ldiruvchining) Telegram ID raqamini yuboring:")
    await state.set_state(AdminStates.waiting_for_pay_admin)

@dp.message(AdminStates.waiting_for_pay_admin)
async def save_pay_admin(message: types.Message, state: FSMContext):
    try:
        new_id = int(message.text.strip())
        if new_id not in db["payment_admins"]:
            db["payment_admins"].append(new_id)
            save_db()
            add_log(f"💳 Hisob admini qo'shildi ID: {new_id}")
            await message.answer(f"✅ ID `{new_id}` hisob admini etib tayinlandi!", parse_mode="Markdown")
        else:
            await message.answer("⚠️ Bu foydalanuvchi allaqachon hisob admini.")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID!")
    await state.clear()

@dp.message(F.text == "➖ Hisob adminini o'chirish")
async def del_pay_admin_start(message: types.Message, state: FSMContext):
    if message.from_user.id != OWNER_ID:
        return
    if not db["payment_admins"]:
        await message.answer("Hisob adminlari yo'q.")
        return
    list_str = "\n".join([str(x) for x in db["payment_admins"]])
    await message.answer(f"Hisob adminlari:\n{list_str}\n\nO'chirmoqchi bo'lgan ID raqamni yuboring:")
    await state.set_state(AdminStates.del_pay_admin)

@dp.message(AdminStates.del_pay_admin)
async def remove_pay_admin(message: types.Message, state: FSMContext):
    try:
        pid = int(message.text.strip())
        if pid in db["payment_admins"]:
            db["payment_admins"].remove(pid)
            save_db()
            add_log(f"❌ Hisob admini o'chirildi ID: {pid}")
            await message.answer("❌ Hisob admini o'chirildi.")
        else:
            await message.answer("Topilmadi.")
    except ValueError:
        await message.answer("❌ Noto'g'ri ID!")
    await state.clear()

# --- BALANSNI O'ZGARTIRISH (Admin va Owner) ---
@dp.message(F.text == "💰 Foydalanuvchi balansini o'zgartirish")
async def change_balance_start(message: types.Message, state: FSMContext):
    if message.from_user.id not in db["admins"] and message.from_user.id != OWNER_ID:
        return
    await message.answer("Foydalanuvchining Telegram ID raqamini yuboring:")
    await state.set_state(AdminStates.user_id_for_balance)

@dp.message(AdminStates.user_id_for_balance)
async def get_user_id_for_balance(message: types.Message, state: FSMContext):
    try:
        uid = int(message.text.strip())
        if uid not in db["users"]:
            db["users"][uid] = {"balance": 0}
        await state.update_data(target_user=uid)
        await message.answer(f"Foydalanuvchi topildi. Hozirgi balansi: {db['users'][uid]['balance']} so'm.\n\nQo'shiladigan (+) yoki ayiriladigan (-) summani yuboring (Masalan: `5000` yoki `-2000`):", parse_mode="Markdown")
        await state.set_state(AdminStates.new_balance_amount)
    except ValueError:
        await message.answer("❌ Noto'g'ri ID!")

@dp.message(AdminStates.new_balance_amount)
async def apply_balance_change(message: types.Message, state: FSMContext):
    try:
        amount = int(message.text.strip())
        data = await state.get_data()
        uid = data["target_user"]
        admin = message.from_user
        
        db["users"][uid]["balance"] += amount
        save_db()
        
        add_log(f"💰 Balans o'zgartirildi: Admin {admin.full_name} -> User {uid} ga {amount:+d} so'm. Yangi balans: {db['users'][uid]['balance']}")

        await message.answer(f"✅ Foydalanuvchi ({uid}) balansi yangilandi! Yangi balans: **{db['users'][uid]['balance']} so'm**", parse_mode="Markdown")
        
        try:
            await bot.send_message(uid, f"💰 Balansingizga o'zgartirish kiritildi! Yangi balans: **{db['users'][uid]['balance']} so'm**", parse_mode="Markdown")
        except:
            pass
            
    except ValueError:
        await message.answer("❌ Faqat raqam kiriting!")
    await state.clear()

# --- RENDER WEB SERVER VA UYG'OTIB TURISH (SELF-PING) ---
async def handle(request):
    return web.Response(text="Bot uyg'oq va ishlayapti!")

async def self_ping():
    """Bot har 5 daqiqada o'zini o'zi ping qilib turadi (uxlab qolmasligi uchun)"""
    await asyncio.sleep(10) # Server to'liq ishga tushishi uchun biroz kutamiz
    port = int(os.environ.get("PORT", 8080))
    # Agar Renderda ishlatayotgan bo'lsangiz RENDER_EXTERNAL_URL avtomatik bo'ladi, 
    # bo'lmasa localhost orqali so'rov tashlaydi
    url = os.environ.get("RENDER_EXTERNAL_URL", f"http://127.0.0.1:{port}")
    
    async with aiohttp.ClientSession() as session:
        while True:
            try:
                async with session.get(url) as response:
                    await response.text()
            except Exception:
                pass
            await asyncio.sleep(300) # Har 5 daqiqada (300 sekund)

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    
    # Self-ping vazifasini ishga tushiramiz
    asyncio.create_task(self_ping())

# --- RUNNER ---
async def main():
    logging.basicConfig(level=logging.INFO)
    asyncio.create_task(start_web_server())
    print("Bot uyg'otish tizimi bilan 100% muvaffaqiyatli ishga tushdi!")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

