import asyncio
import json
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

# =========================================================
# SOZLAMALAR
# =========================================================

TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 7020448136
DB_FILE = "database.json"

if not TOKEN:
    raise RuntimeError("8644696840:AAFhsRFaMsz8XrySdMV4kAVAJ4RbITaJT34)

bot = Bot(token=TOKEN)
dp = Dispatcher()

# =========================================================
# DATABASE
# =========================================================

def default_db():
    return {
        "users": {
            str(OWNER_ID): {
                "balance": 0
            }
        },
        "admins": [
            OWNER_ID
        ],
        "req_channels": [],
        "sub_channels": [],
        "payment_admins": [],
        "logs": [],
        "promos": {
            "42": [],
            "79": [],
            "99": [],
            "299": []
        }
    }


def load_db():
    if not os.path.exists(DB_FILE):
        return default_db()

    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)

        data.setdefault("users", {})
        data.setdefault("admins", [OWNER_ID])
        data.setdefault("req_channels", [])
        data.setdefault("sub_channels", [])
        data.setdefault("payment_admins", [])
        data.setdefault("logs", [])
        data.setdefault(
            "promos",
            {
                "42": [],
                "79": [],
                "99": [],
                "299": []
            }
        )

        return data

    except Exception:
        logging.exception("database.json o'qilmadi")
        return default_db()


db = load_db()


def save_db():
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(
            db,
            f,
            ensure_ascii=False,
            indent=4
        )


def add_user(user_id: int):
    uid = str(user_id)

    if uid not in db["users"]:
        db["users"][uid] = {
            "balance": 0
        }
        save_db()


def get_balance(user_id: int):
    return db["users"].get(
        str(user_id),
        {"balance": 0}
    ).get("balance", 0)


def set_balance(user_id: int, amount: int):
    add_user(user_id)
    db["users"][str(user_id)]["balance"] = amount
    save_db()


def add_log(text: str):
    db["logs"].append(text)
    db["logs"] = db["logs"][-100:]
    save_db()


# =========================================================
# FSM
# =========================================================

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


# =========================================================
# RUXSAT TEKSHIRISH
# =========================================================

def is_owner(user_id: int):
    return user_id == OWNER_ID


def is_admin(user_id: int):
    return user_id == OWNER_ID or user_id in db["admins"]


# =========================================================
# KANAL YORDAMCHI FUNKSIYALARI
# =========================================================

def normalize_channel(text: str):
    text = text.strip()

    if text.startswith("https://t.me/"):
        text = "@" + text.split("https://t.me/")[1].split("/")[0]

    if text.startswith("t.me/"):
        text = "@" + text.split("t.me/")[1].split("/")[0]

    if not text.startswith("@") and not text.startswith("-100"):
        text = "@" + text

    return text


async def get_channel_name(channel):
    try:
        chat = await bot.get_chat(channel)
        return chat.title
    except Exception:
        return str(channel)


# =========================================================
# OBUNANI TEKSHIRISH
# =========================================================

async def check_one_channel(user_id: int, channel: str):

    try:
        member = await bot.get_chat_member(
            chat_id=channel,
            user_id=user_id
        )

        # Foydalanuvchi kanalga kirgan bo'lishi kerak
        if member.status in (
            "member",
            "administrator",
            "creator"
        ):
            return True

        # restricted holatda ham is_member True bo'lishi mumkin
        if member.status == "restricted":
            return getattr(member, "is_member", False)

        return False

    except Exception as e:
        logging.warning(
            f"Kanal tekshirish xatosi {channel}: {e}"
        )

        # Xatoni "obuna bo'lgan" deb hisoblamaymiz
        return False


async def check_subscription(user_id: int):

    all_channels = (
        db["sub_channels"]
        + db["req_channels"]
    )

    if not all_channels:
        return True

    for channel in all_channels:

        ok = await check_one_channel(
            user_id,
            channel
        )

        if not ok:
            return False

    return True


# =========================================================
# OBUNA TUGMALARI
# =========================================================

async def get_sub_keyboard():

    rows = []

    for channel in (
        db["sub_channels"]
        + db["req_channels"]
    ):

        try:
            chat = await bot.get_chat(channel)

            if chat.username:
                url = f"https://t.me/{chat.username}"
            else:
                # Private kanal uchun username bo'lmasa,
                # admin invite linkini alohida ishlatish kerak.
                url = None

            if url:
                rows.append([
                    InlineKeyboardButton(
                        text=f"📢 {chat.title}",
                        url=url
                    )
                ])

            else:
                rows.append([
                    InlineKeyboardButton(
                        text=f"📢 {chat.title}",
                        callback_data="no_link"
                    )
                ])

        except Exception:
            rows.append([
                InlineKeyboardButton(
                    text=f"📢 {channel}",
                    callback_data="no_link"
                )
            ])

    rows.append([
        InlineKeyboardButton(
            text="✅ Obunani tekshirish",
            callback_data="check_sub"
        )
    ])

    return InlineKeyboardMarkup(
        inline_keyboard=rows
    )


# =========================================================
# MENYU
# =========================================================

def get_main_menu(user_id):

    keyboard = [
        [
            KeyboardButton(
                text="📦 Bulldrop"
            )
        ],
        [
            KeyboardButton(
                text="💳 Balans"
            ),
            KeyboardButton(
                text="➕ Balans to'ldirish"
            )
        ]
    ]

    if is_admin(user_id):
        keyboard.append([
            KeyboardButton(
                text="⚙️ Admin Panel"
            )
        ])

    if is_owner(user_id):
        keyboard.append([
            KeyboardButton(
                text="👑 Owner Panel"
            )
        ])

    return ReplyKeyboardMarkup(
        keyboard=keyboard,
        resize_keyboard=True
    )


# =========================================================
# START
# =========================================================

@dp.message(Command("start"))
async def cmd_start(message: types.Message):

    user_id = message.from_user.id

    add_user(user_id)

    if not await check_subscription(user_id):

        await message.answer(
            "⚠️ <b>Botdan foydalanish uchun quyidagi "
            "kanallarga obuna bo'ling:</b>",
            reply_markup=await get_sub_keyboard(),
            parse_mode="HTML"
        )

        return

    await message.answer(
        "🏠 <b>Bosh sahifa</b>\n\n"
        "Quyidagi bo'limlardan birini tanlang:",
        reply_markup=get_main_menu(user_id),
        parse_mode="HTML"
    )


# =========================================================
# JOIN REQUEST
# =========================================================

@dp.chat_join_request()
async def handle_join_request(
    request: types.ChatJoinRequest
):

    user_id = request.from_user.id
    chat_id = request.chat.id

    # Faqat bizning req_channels ichidagi kanallar
    allowed = False

    for channel in db["req_channels"]:
        try:
            chat = await bot.get_chat(channel)

            if chat.id == chat_id:
                allowed = True
                break

        except Exception:
            pass

    if not allowed:
        return

    try:
        # Join Requestni avtomatik tasdiqlaymiz
        await bot.approve_chat_join_request(
            chat_id=chat_id,
            user_id=user_id
        )

        add_user(user_id)

        add_log(
            f"✅ Join Request tasdiqlandi: "
            f"{user_id} -> {chat_id}"
        )

        try:
            await bot.send_message(
                user_id,
                "✅ Kanalga obuna bo'lish so'rovingiz "
                "tasdiqlandi!\n\n"
                "Endi botdan foydalanishingiz mumkin."
            )
        except Exception:
            pass

    except Exception as e:

        logging.exception(
            f"Join Request tasdiqlash xatosi: {e}"
        )


@dp.callback_query(F.data == "no_link")
async def no_link(callback: types.CallbackQuery):

    await callback.answer(
        "Bu kanal uchun havola sozlanmagan.",
        show_alert=True
    )


# =========================================================
# OBUNANI TEKSHIRISH
# =========================================================

@dp.callback_query(F.data == "check_sub")
async def check_sub_callback(
    callback: types.CallbackQuery
):

    user_id = callback.from_user.id

    if await check_subscription(user_id):

        try:
            await callback.message.delete()
        except Exception:
            pass

        await callback.message.answer(
            "🏠 <b>Bosh sahifa</b>",
            reply_markup=get_main_menu(user_id),
            parse_mode="HTML"
        )

    else:

        await callback.answer(
            "❌ Hali barcha kanallarga obuna bo'lmagansiz!",
            show_alert=True
        )


# =========================================================
# BOSH MENYU
# =========================================================

@dp.message(F.text == "🏠 Bosh menyu")
async def back_to_menu(message: types.Message):

    user_id = message.from_user.id

    if not await check_subscription(user_id):

        await message.answer(
            "⚠️ Avval kanallarga obuna bo'ling!",
            reply_markup=await get_sub_keyboard()
        )

        return

    await message.answer(
        "🏠 <b>Bosh sahifa:</b>",
        reply_markup=get_main_menu(user_id),
        parse_mode="HTML"
    )


# =========================================================
# BULLDROP
# =========================================================

PRICES = {
    "42": 3500,
    "79": 5500,
    "99": 8000,
    "299": 22000
}


@dp.message(F.text == "📦 Bulldrop")
async def bulldrop_menu(message: types.Message):

    user_id = message.from_user.id

    if not await check_subscription(user_id):

        await message.answer(
            "⚠️ Avval kanallarga obuna bo'ling!",
            reply_markup=await get_sub_keyboard()
        )

        return

    rows = []

    for code_type, price in PRICES.items():

        count = len(
            db["promos"].get(
                code_type,
                []
            )
        )

        rows.append([
            InlineKeyboardButton(
                text=(
                    f"🎁 {code_type} – "
                    f"{price:,} so'm "
                    f"({count} ta bor)"
                ),
                callback_data=f"buy_{code_type}"
            )
        ])

    await message.answer(
        "📦 <b>Bulldrop promokodlari</b>\n\n"
        "Sotib olmoqchi bo'lgan promokodingizni tanlang:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
        parse_mode="HTML"
    )


# =========================================================
# XARID QOIDASI
# =========================================================

@dp.callback_query(F.data.startswith("buy_"))
async def ask_rules(
    callback: types.CallbackQuery
):

    code_type = callback.data.split("_")[1]

    rule_text = (
        "⚠️ <b>Muhim xarid qoidasi!</b>\n\n"
        "📹 Xarid qilishdan oldin ekran yozuvini "
        "yoqing.\n\n"
        "Botdan kod olinishi va undan foydalanish "
        "jarayoni uzluksiz ko'rinishi kerak."
    )

    keyboard = [
        [
            InlineKeyboardButton(
                text="✅ Roziman",
                callback_data=f"accept_{code_type}"
            ),
            InlineKeyboardButton(
                text="❌ Bekor qilish",
                callback_data="cancel_rules"
            )
        ]
    ]

    await callback.message.answer(
        rule_text,
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        ),
        parse_mode="HTML"
    )

    await callback.answer()


@dp.callback_query(F.data == "cancel_rules")
async def cancel_purchase(
    callback: types.CallbackQuery
):

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "❌ Xarid bekor qilindi."
    )

    await callback.answer()


# =========================================================
# XARID
# =========================================================

@dp.callback_query(F.data.startswith("accept_"))
async def finish_purchase(
    callback: types.CallbackQuery
):

    user_id = callback.from_user.id
    code_type = callback.data.split("_")[1]

    if not await check_subscription(user_id):

        await callback.answer(
            "❌ Avval kanallarga obuna bo'ling!",
            show_alert=True
        )

        return

    price = PRICES[code_type]

    add_user(user_id)

    balance = get_balance(user_id)

    if balance < price:

        await callback.answer(
            f"❌ Balansingiz yetarli emas!\n"
            f"Balans: {balance:,} so'm",
            show_alert=True
        )

        return

    if not db["promos"].get(code_type):

        await callback.answer(
            "❌ Bu turdagi promokod qolmagan.",
            show_alert=True
        )

        return

    promo_code = db["promos"][code_type].pop(0)

    new_balance = balance - price

    set_balance(
        user_id,
        new_balance
    )

    add_log(
        f"🛒 Xarid: "
        f"{callback.from_user.full_name} "
        f"({user_id}) - "
        f"{code_type} tur - "
        f"{price} so'm"
    )

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        "🎉 <b>Xarid muvaffaqiyatli!</b>\n\n"
        f"🎁 Promokodingiz:\n"
        f"<code>{promo_code}</code>\n\n"
        f"💰 Qolgan balans: {new_balance:,} so'm",
        parse_mode="HTML"
    )

    await callback.answer()


# =========================================================
# BALANS
# =========================================================

@dp.message(F.text == "💳 Balans")
async def show_balance(
    message: types.Message
):

    user_id = message.from_user.id

    add_user(user_id)

    balance = get_balance(user_id)

    await message.answer(
        f"🆔 ID: <code>{user_id}</code>\n"
        f"💰 Balans: <b>{balance:,} so'm</b>",
        parse_mode="HTML"
    )


# =========================================================
# BALANS TO'LDIRISH
# =========================================================

@dp.message(F.text == "➕ Balans to'ldirish")
async def top_up_balance(
    message: types.Message
):

    if not db["payment_admins"]:

        await message.answer(
            "💳 Hozircha hisob admini tayinlanmagan."
        )

        return

    rows = []

    for pid in db["payment_admins"]:

        try:
            user = await bot.get_chat(pid)

            if user.username:

                rows.append([
                    InlineKeyboardButton(
                        text=f"👤 @{user.username}",
                        url=f"https://t.me/{user.username}"
                    )
                ])

            else:

                rows.append([
                    InlineKeyboardButton(
                        text="👤 Hisob admini",
                        url=f"tg://user?id={pid}"
                    )
                ])

        except Exception:

            rows.append([
                InlineKeyboardButton(
                    text=f"👤 ID: {pid}",
                    url=f"tg://user?id={pid}"
                )
            ])

    await message.answer(
        "💳 <b>Balans to'ldirish</b>\n\n"
        "Quyidagi hisob adminiga murojaat qiling "
        "va to'lov chekini yuboring:",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=rows
        ),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@dp.message(F.text == "⚙️ Admin Panel")
async def admin_panel(
    message: types.Message
):

    if not is_admin(message.from_user.id):
        return

    keyboard = [
        [
            KeyboardButton(
                text="➕ Promokod qo'shish"
            ),
            KeyboardButton(
                text="📊 Statistika"
            )
        ],
        [
            KeyboardButton(
                text="➕ Majburiy kanal"
            ),
            KeyboardButton(
                text="➖ Majburiy kanalni o'chirish"
            )
        ],
        [
            KeyboardButton(
                text="➕ So'rovli kanal"
            ),
            KeyboardButton(
                text="➖ So'rovli kanalni o'chirish"
            )
        ],
        [
            KeyboardButton(
                text="📢 Xabar yuborish (Reklama)"
            )
        ],
        [
            KeyboardButton(
                text="💰 Foydalanuvchi balansini o'zgartirish"
            )
        ],
        [
            KeyboardButton(
                text="🏠 Bosh menyu"
            )
        ]
    ]

    await message.answer(
        "⚙️ <b>Admin Boshqaruv Paneli</b>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )


# =========================================================
# STATISTIKA
# =========================================================

@dp.message(F.text == "📊 Statistika")
async def stats(message: types.Message):

    if not is_admin(message.from_user.id):
        return

    total_users = len(db["users"])

    text = (
        "📊 <b>Statistika</b>\n\n"
        f"👥 Foydalanuvchilar: {total_users}\n\n"
        "📦 <b>Qolgan promokodlar:</b>\n"
    )

    for code_type in PRICES:
        text += (
            f"• {code_type}-tur: "
            f"{len(db['promos'].get(code_type, []))} ta\n"
        )

    text += (
        f"\n📢 Majburiy kanallar: "
        f"{len(db['sub_channels'])}\n"
        f"🔔 So'rovli kanallar: "
        f"{len(db['req_channels'])}"
    )

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# PROMOKOD QO'SHISH
# =========================================================

@dp.message(F.text == "➕ Promokod qo'shish")
async def add_promo_menu(
    message: types.Message
):

    if not is_admin(message.from_user.id):
        return

    keyboard = [
        [
            InlineKeyboardButton(
                text="42",
                callback_data="add_p_42"
            ),
            InlineKeyboardButton(
                text="79",
                callback_data="add_p_79"
            )
        ],
        [
            InlineKeyboardButton(
                text="99",
                callback_data="add_p_99"
            ),
            InlineKeyboardButton(
                text="299",
                callback_data="add_p_299"
            )
        ]
    ]

    await message.answer(
        "Qaysi turdagi promokod qo'shmoqchisiz?",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=keyboard
        )
    )


@dp.callback_query(F.data.startswith("add_p_"))
async def add_promo_type(
    callback: types.CallbackQuery,
    state: FSMContext
):

    if not is_admin(callback.from_user.id):
        return

    code_type = callback.data.split("_")[2]

    await state.update_data(
        code_type=code_type
    )

    await callback.message.answer(
        f"OK!\n\n"
        f"<b>{code_type}</b> turidagi kodlarni yuboring.\n"
        f"Har bir kodni yangi qatordan yozing.",
        parse_mode="HTML"
    )

    await state.set_state(
        AdminStates.waiting_for_promo
    )

    await callback.answer()


@dp.message(AdminStates.waiting_for_promo)
async def save_promo_handler(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    if not message.text:
        await message.answer(
            "❌ Kodlarni matn ko'rinishida yuboring."
        )
        return

    data = await state.get_data()
    code_type = data["code_type"]

    codes = message.text.splitlines()

    added = 0

    for code in codes:

        code = code.strip()

        if code:
            db["promos"][code_type].append(code)
            added += 1

    save_db()

    add_log(
        f"➕ {message.from_user.id} "
        f"{code_type}-turga {added} ta kod qo'shdi."
    )

    await message.answer(
        f"✅ {added} ta promokod qo'shildi."
    )

    await state.clear()


# =========================================================
# MAJBURIY KANAL
# =========================================================

@dp.message(F.text == "➕ Majburiy kanal")
async def add_sub_ch_start(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "📢 Majburiy kanal username'ini yuboring.\n\n"
        "Masalan:\n"
        "<code>@kanal_username</code>",
        parse_mode="HTML"
    )

    await state.set_state(
        AdminStates.waiting_for_sub_ch
    )


@dp.message(AdminStates.waiting_for_sub_ch)
async def save_sub_ch(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    ch = normalize_channel(
        message.text
    )

    if ch not in db["sub_channels"]:

        # Kanalni tekshiramiz
        try:
            await bot.get_chat(ch)

            db["sub_channels"].append(ch)
            save_db()

            add_log(
                f"📢 Majburiy kanal qo'shildi: {ch}"
            )

            await message.answer(
                f"✅ Majburiy kanal qo'shildi:\n"
                f"{ch}\n\n"
                f"⚠️ Botni shu kanalga administrator "
                f"qilish kerak."
            )

        except Exception:

            await message.answer(
                "❌ Kanal topilmadi.\n\n"
                "Username to'g'ri ekanini tekshiring "
                "va bot kanalga kirganini tekshiring."
            )

    else:

        await message.answer(
            "⚠️ Bu kanal allaqachon mavjud."
        )

    await state.clear()


# =========================================================
# MAJBURIY KANAL O'CHIRISH
# =========================================================

@dp.message(F.text == "➖ Majburiy kanalni o'chirish")
async def del_sub_ch_start(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not db["sub_channels"]:

        await message.answer(
            "Hozircha majburiy kanallar yo'q."
        )

        return

    await message.answer(
        "O'chirmoqchi bo'lgan kanal username'ini yuboring:\n\n"
        + "\n".join(db["sub_channels"])
    )

    await state.set_state(
        AdminStates.del_sub_ch
    )


@dp.message(AdminStates.del_sub_ch)
async def remove_sub_ch(
    message: types.Message,
    state: FSMContext
):

    ch = normalize_channel(
        message.text
    )

    if ch in db["sub_channels"]:

        db["sub_channels"].remove(ch)
        save_db()

        add_log(
            f"❌ Majburiy kanal o'chirildi: {ch}"
        )

        await message.answer(
            "✅ Kanal o'chirildi."
        )

    else:

        await message.answer(
            "❌ Kanal topilmadi."
        )

    await state.clear()


# =========================================================
# SO'ROVLI KANAL
# =========================================================

@dp.message(F.text == "➕ So'rovli kanal")
async def add_req_ch_start(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "🔔 <b>Haqiqiy so'rovli kanal qo'shish</b>\n\n"
        "Kanal username'ini yuboring:\n"
        "<code>@kanal_username</code>\n\n"
        "⚠️ Kanalda Join Request yoqilgan bo'lishi "
        "va bot kanalga administrator qilingan bo'lishi kerak.",
        parse_mode="HTML"
    )

    await state.set_state(
        AdminStates.waiting_for_req_ch
    )


@dp.message(AdminStates.waiting_for_req_ch)
async def save_req_ch(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    ch = normalize_channel(
        message.text
    )

    if ch in db["req_channels"]:

        await message.answer(
            "⚠️ Bu kanal allaqachon mavjud."
        )

        await state.clear()
        return

    try:

        chat = await bot.get_chat(ch)

        # Botning admin ekanini tekshirish
        me = await bot.get_me()

        member = await bot.get_chat_member(
            chat_id=chat.id,
            user_id=me.id
        )

        if member.status not in (
            "administrator",
            "creator"
        ):

            await message.answer(
                "❌ Bot bu kanalga administrator qilinmagan."
            )

            await state.clear()
            return

        db["req_channels"].append(ch)

        save_db()

        add_log(
            f"🔔 So'rovli kanal qo'shildi: {ch}"
        )

        await message.answer(
            f"✅ So'rovli kanal qo'shildi:\n"
            f"{chat.title}\n\n"
            f"Endi foydalanuvchi kanalga Join Request "
            f"yuborsa, bot uni avtomatik tasdiqlaydi."
        )

    except Exception as e:

        logging.exception(
            f"So'rovli kanal qo'shish xatosi: {e}"
        )

        await message.answer(
            "❌ Kanalni qo'shib bo'lmadi.\n\n"
            "Tekshiring:\n"
            "1. Username to'g'ri\n"
            "2. Bot kanalga administrator\n"
            "3. Kanal Join Requestni qo'llab-quvvatlaydi"
        )

    await state.clear()


# =========================================================
# SO'ROVLI KANAL O'CHIRISH
# =========================================================

@dp.message(F.text == "➖ So'rovli kanalni o'chirish")
async def del_req_ch_start(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    if not db["req_channels"]:

        await message.answer(
            "Hozircha so'rovli kanallar yo'q."
        )

        return

    await message.answer(
        "O'chirmoqchi bo'lgan kanal username'ini yuboring:\n\n"
        + "\n".join(db["req_channels"])
    )

    await state.set_state(
        AdminStates.del_req_ch
    )


@dp.message(AdminStates.del_req_ch)
async def remove_req_ch(
    message: types.Message,
    state: FSMContext
):

    ch = normalize_channel(
        message.text
    )

    if ch in db["req_channels"]:

        db["req_channels"].remove(ch)
        save_db()

        add_log(
            f"❌ So'rovli kanal o'chirildi: {ch}"
        )

        await message.answer(
            "✅ So'rovli kanal o'chirildi."
        )

    else:

        await message.answer(
            "❌ Kanal topilmadi."
        )

    await state.clear()


# =========================================================
# OWNER PANEL
# =========================================================

@dp.message(F.text == "👑 Owner Panel")
async def owner_panel(
    message: types.Message
):

    if not is_owner(message.from_user.id):
        return

    keyboard = [
        [
            KeyboardButton(
                text="➕ Admin qo'shish"
            ),
            KeyboardButton(
                text="➖ Adminni o'chirish"
            )
        ],
        [
            KeyboardButton(
                text="➕ Hisob admini qo'shish"
            ),
            KeyboardButton(
                text="➖ Hisob adminini o'chirish"
            )
        ],
        [
            KeyboardButton(
                text="📜 Tarix (Logs) bo'limi"
            )
        ],
        [
            KeyboardButton(
                text="🏠 Bosh menyu"
            )
        ]
    ]

    await message.answer(
        "👑 <b>Owner Panel</b>",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=keyboard,
            resize_keyboard=True
        ),
        parse_mode="HTML"
    )


# =========================================================
# ADMIN QO'SHISH
# =========================================================

@dp.message(F.text == "➕ Admin qo'shish")
async def add_admin_start(
    message: types.Message,
    state: FSMContext
):

    if not is_owner(message.from_user.id):
        return

    await message.answer(
        "Yangi adminning Telegram ID raqamini yuboring:"
    )

    await state.set_state(
        AdminStates.waiting_for_admin
    )


@dp.message(AdminStates.waiting_for_admin)
async def save_admin(
    message: types.Message,
    state: FSMContext
):

    if not is_owner(message.from_user.id):
        await state.clear()
        return

    try:

        new_id = int(
            message.text.strip()
        )

        if new_id not in db["admins"]:

            db["admins"].append(new_id)
            save_db()

            add_log(
                f"👑 Admin qo'shildi: {new_id}"
            )

            await message.answer(
                f"✅ {new_id} admin qilindi."
            )

        else:

            await message.answer(
                "⚠️ Bu foydalanuvchi allaqachon admin."
            )

    except ValueError:

        await message.answer(
            "❌ ID faqat raqam bo'lishi kerak."
        )

    await state.clear()


# =========================================================
# ADMIN O'CHIRISH
# =========================================================

@dp.message(F.text == "➖ Adminni o'chirish")
async def del_admin_start(
    message: types.Message,
    state: FSMContext
):

    if not is_owner(message.from_user.id):
        return

    admins = [
        str(x)
        for x in db["admins"]
        if x != OWNER_ID
    ]

    if not admins:

        await message.answer(
            "Boshqa adminlar yo'q."
        )

        return

    await message.answer(
        "O'chirmoqchi bo'lgan admin ID'sini yuboring:\n\n"
        + "\n".join(admins)
    )

    await state.set_state(
        AdminStates.del_admin
    )


@dp.message(AdminStates.del_admin)
async def remove_admin(
    message: types.Message,
    state: FSMContext
):

    if not is_owner(message.from_user.id):
        await state.clear()
        return

    try:

        adm_id = int(
            message.text.strip()
        )

        if adm_id == OWNER_ID:

            await message.answer(
                "❌ Ownerni o'chirib bo'lmaydi."
            )

        elif adm_id in db["admins"]:

            db["admins"].remove(adm_id)
            save_db()

            add_log(
                f"❌ Admin o'chirildi: {adm_id}"
            )

            await message.answer(
                "✅ Admin o'chirildi."
            )

        else:

            await message.answer(
                "❌ Admin topilmadi."
            )

    except ValueError:

        await message.answer(
            "❌ Noto'g'ri ID."
        )

    await state.clear()


# =========================================================
# HISOB ADMINI QO'SHISH
# =========================================================

@dp.message(F.text == "➕ Hisob admini qo'shish")
async def add_pay_admin_start(
    message: types.Message,
    state: FSMContext
):

    if not is_owner(message.from_user.id):
        return

    await message.answer(
        "Hisob adminining Telegram ID raqamini yuboring:"
    )

    await state.set_state(
        AdminStates.waiting_for_pay_admin
    )


@dp.message(AdminStates.waiting_for_pay_admin)
async def save_pay_admin(
    message: types.Message,
    state: FSMContext
):

    if not is_owner(message.from_user.id):
        await state.clear()
        return

    try:

        pid = int(
            message.text.strip()
        )

        if pid not in db["payment_admins"]:

            db["payment_admins"].append(pid)
            save_db()

            add_log(
                f"💳 Hisob admini qo'shildi: {pid}"
            )

            await message.answer(
                "✅ Hisob admini qo'shildi."
            )

        else:

            await message.answer(
                "⚠️ Bu foydalanuvchi allaqachon hisob admini."
            )

    except ValueError:

        await message.answer(
            "❌ Noto'g'ri ID."
        )

    await state.clear()


# =========================================================
# HISOB ADMINI O'CHIRISH
# =========================================================

@dp.message(F.text == "➖ Hisob adminini o'chirish")
async def del_pay_admin_start(
    message: types.Message,
    state: FSMContext
):

    if not is_owner(message.from_user.id):
        return

    if not db["payment_admins"]:

        await message.answer(
            "Hisob adminlari yo'q."
        )

        return

    await message.answer(
        "O'chirmoqchi bo'lgan ID raqamni yuboring:\n\n"
        + "\n".join(
            str(x)
            for x in db["payment_admins"]
        )
    )

    await state.set_state(
        AdminStates.del_pay_admin
    )


@dp.message(AdminStates.del_pay_admin)
async def remove_pay_admin(
    message: types.Message,
    state: FSMContext
):

    if not is_owner(message.from_user.id):
        await state.clear()
        return

    try:

        pid = int(
            message.text.strip()
        )

        if pid in db["payment_admins"]:

            db["payment_admins"].remove(pid)
            save_db()

            add_log(
                f"❌ Hisob admini o'chirildi: {pid}"
            )

            await message.answer(
                "✅ Hisob admini o'chirildi."
            )

        else:

            await message.answer(
                "❌ Topilmadi."
            )

    except ValueError:

        await message.answer(
            "❌ Noto'g'ri ID."
        )

    await state.clear()


# =========================================================
# LOGS
# =========================================================

@dp.message(F.text == "📜 Tarix (Logs) bo'limi")
async def show_logs(
    message: types.Message
):

    if not is_owner(message.from_user.id):
        return

    if not db["logs"]:

        await message.answer(
            "📜 Hozircha tarix bo'sh."
        )

        return

    logs = db["logs"][-30:]

    text = (
        "📜 <b>Oxirgi harakatlar:</b>\n\n"
        + "\n".join(logs)
    )

    if len(text) > 4000:
        text = text[-4000:]

    await message.answer(
        text,
        parse_mode="HTML"
    )


# =========================================================
# BALANS O'ZGARTIRISH
# =========================================================

@dp.message(F.text == "💰 Foydalanuvchi balansini o'zgartirish")
async def change_balance_start(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "Foydalanuvchining Telegram ID raqamini yuboring:"
    )

    await state.set_state(
        AdminStates.user_id_for_balance
    )


@dp.message(AdminStates.user_id_for_balance)
async def get_user_id_for_balance(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    try:

        uid = int(
            message.text.strip()
        )

        add_user(uid)

        await state.update_data(
            target_user=uid
        )

        await message.answer(
            f"🆔 ID: {uid}\n"
            f"💰 Hozirgi balans: "
            f"{get_balance(uid):,} so'm\n\n"
            f"Qo'shiladigan yoki ayiriladigan "
            f"summani yuboring.\n\n"
            f"Masalan:\n"
            f"<code>5000</code>\n"
            f"<code>-2000</code>",
            parse_mode="HTML"
        )

        await state.set_state(
            AdminStates.new_balance_amount
        )

    except ValueError:

        await message.answer(
            "❌ ID faqat raqam bo'lishi kerak."
        )


@dp.message(AdminStates.new_balance_amount)
async def apply_balance_change(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    try:

        amount = int(
            message.text.strip()
        )

        data = await state.get_data()
        uid = data["target_user"]

        old_balance = get_balance(uid)
        new_balance = old_balance + amount

        if new_balance < 0:

            await message.answer(
                "❌ Balans 0 dan past bo'lishi mumkin emas."
            )

            await state.clear()
            return

        set_balance(
            uid,
            new_balance
        )

        add_log(
            f"💰 Balans: "
            f"Admin {message.from_user.id} -> "
            f"{uid}: {amount:+d} so'm"
        )

        await message.answer(
            f"✅ Balans o'zgartirildi.\n\n"
            f"🆔 ID: {uid}\n"
            f"💰 Yangi balans: "
            f"<b>{new_balance:,} so'm</b>",
            parse_mode="HTML"
        )

        try:

            await bot.send_message(
                uid,
                f"💰 Balansingiz o'zgartirildi.\n\n"
                f"Yangi balans: "
                f"<b>{new_balance:,} so'm</b>",
                parse_mode="HTML"
            )

        except Exception:
            pass

    except ValueError:

        await message.answer(
            "❌ Faqat raqam kiriting."
        )

    await state.clear()


# =========================================================
# REKLAMA
# =========================================================

@dp.message(F.text == "📢 Xabar yuborish (Reklama)")
async def broadcast_start(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        return

    await message.answer(
        "📢 Barcha foydalanuvchilarga yubormoqchi "
        "bo'lgan xabarni yuboring.\n\n"
        "Matn, rasm yoki video bo'lishi mumkin."
    )

    await state.set_state(
        AdminStates.broadcast_text
    )


@dp.message(AdminStates.broadcast_text)
async def broadcast_send(
    message: types.Message,
    state: FSMContext
):

    if not is_admin(message.from_user.id):
        await state.clear()
        return

    users = list(db["users"].keys())

    success = 0
    fail = 0

    await message.answer(
        "⏳ Reklama yuborish boshlandi..."
    )

    for uid in users:

        try:

            await message.send_copy(
                chat_id=int(uid)
            )

            success += 1

            # Telegram flood limitini kamaytirish
            await asyncio.sleep(0.08)

        except Exception:

            fail += 1

    add_log(
        f"📢 Reklama: "
        f"{success} muvaffaqiyatli, "
        f"{fail} xato"
    )

    await message.answer(
        f"✅ Reklama tugadi.\n\n"
        f"Yuborildi: {success}\n"
        f"Yetib bormadi: {fail}"
    )

    await state.clear()


# =========================================================
# WEB SERVER - RENDER
# =========================================================

async def handle(request):
    return web.Response(
        text="Bot ishlayapti!"
    )


async def start_web_server():

    app = web.Application()

    app.router.add_get(
        "/",
        handle
    )

    runner = web.AppRunner(app)

    await runner.setup()

    port = int(
        os.environ.get(
            "PORT",
            "10000"
        )
    )

    site = web.TCPSite(
        runner,
        "0.0.0.0",
        port
    )

    await site.start()

    logging.info(
        f"Web server port {port} da ishga tushdi."
    )


# =========================================================
# SELF PING
# =========================================================

async def self_ping():

    await asyncio.sleep(15)

    render_url = os.getenv(
        "RENDER_EXTERNAL_URL"
    )

    if not render_url:
        logging.info(
            "RENDER_EXTERNAL_URL topilmadi."
        )
        return

    import aiohttp

    timeout = aiohttp.ClientTimeout(
        total=20
    )

    async with aiohttp.ClientSession(
        timeout=timeout
    ) as session:

        while True:

            try:

                async with session.get(
                    render_url
                ) as response:

                    logging.info(
                        f"Self ping: {response.status}"
                    )

            except Exception as e:

                logging.warning(
                    f"Self ping xatosi: {e}"
                )

            await asyncio.sleep(300)


# =========================================================
# MAIN
# =========================================================

async def main():

    logging.basicConfig(
        level=logging.INFO
    )

    await start_web_server()

    # Render free xizmatida uxlab qolishni
    # kamaytirish uchun ping.
    asyncio.create_task(
        self_ping()
    )

    # Eski webhookni o'chiramiz
    await bot.delete_webhook(
        drop_pending_updates=True
    )

    logging.info(
        "================================="
    )
    logging.info(
        "BOT ISHGA TUSHDI"
    )
    logging.info(
        "================================="
    )

    await dp.start_polling(
        bot,
        allowed_updates=dp.resolve_used_update_types()
    )


if __name__ == "__main__":

    try:
        asyncio.run(main())

    except KeyboardInterrupt:
        print("Bot to'xtatildi.")
