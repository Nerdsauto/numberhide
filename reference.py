import os
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_polling
from PIL import Image
import easyocr
import numpy as np
import cv2
import io
from difflib import SequenceMatcher

API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

reader = easyocr.Reader(['en'], gpu=False)

STICKERS = {
    "Real Auto": "Real.png",
    "Nerds Auto": "Nerds.png",
    "Jalil Auto": "Jalil.png"
}

REFERENCE_IMAGE_PATH = "reference_plate.jpeg"
REFERENCE_TEXT = ""

def load_reference_plate():
    global REFERENCE_TEXT
    ref_img = cv2.imread(REFERENCE_IMAGE_PATH)
    results = reader.readtext(ref_img)
    if results:
        REFERENCE_TEXT = results[0][1].replace(" ", "").upper()

load_reference_plate()

user_projects = {}
user_waiting = set()

@dp.message_handler(commands=['start'])
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    user_projects[user_id] = []
    user_waiting.discard(user_id)  # foydalanuvchining eski holatini tozalaymiz
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📷 Rasm almashtirish"))
    await message.reply("Assalomu alaykum!\nRasm yuboring (bir yoki bir nechta).", reply_markup=keyboard)

@dp.message_handler(lambda msg: msg.text == "📷 Rasm almashtirish")
async def reset_session(message: types.Message):
    user_id = message.from_user.id
    user_projects[user_id] = []
    user_waiting.discard(user_id)
    await message.reply("Yangi loyiha boshlandi. Endi rasm yuboring.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def collect_photos(message: types.Message):
    user_id = message.from_user.id
    photo = message.photo[-1]
    photo_bytes = await photo.download(destination=io.BytesIO())
    photo_bytes.seek(0)

    if user_id not in user_projects:
        user_projects[user_id] = []
    user_projects[user_id].append(photo_bytes.read())

    if user_id not in user_waiting:
        user_waiting.add(user_id)
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
        for label in STICKERS:
            keyboard.add(KeyboardButton(label))
        await message.reply("Qaysi logotipni qo'yay?", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text in STICKERS)
async def apply_sticker_batch(message: types.Message):
    user_id = message.from_user.id
    user_waiting.discard(user_id)  # ❗️foydalanuvchi stiker tanlagan — endi kutishdan chiqaramiz

    if user_id not in user_projects or not user_projects[user_id]:
        await message.reply("Iltimos, avval rasm yuboring.")
        return

    await message.reply("🛠 Ishlanmoqda...")

    selected_sticker = STICKERS[message.text]
    for image_bytes in user_projects[user_id]:
        result = overlay_sticker(image_bytes, selected_sticker)
        if result:
            await message.reply_photo(photo=types.InputFile(result, filename='modified.jpg'))
        else:
            await message.reply("❌ Raqam topilmadi.")
            await message.reply_photo(photo=types.InputFile(io.BytesIO(image_bytes), filename='original.jpg'))

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📷 Rasm almashtirish"))
    await message.reply("✅ Tayyor. Yana almashtirmoqchi bo‘lsangiz menyudan foydalaning.", reply_markup=keyboard)
    user_projects[user_id] = []

def overlay_sticker(image_bytes, sticker_path):
    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
        cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)
        results = reader.readtext(cv_img)

        best_match = None
        best_ratio = 0.0

        for (bbox, text, prob) in results:
            candidate = text.replace(" ", "").upper()
            ratio = SequenceMatcher(None, candidate, REFERENCE_TEXT).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = (bbox, candidate)

        if best_match and best_ratio > 0.1:
            (tl, tr, br, bl) = best_match[0]
            x_min = int(min(tl[0], bl[0]))
            y_min = int(min(tl[1], tr[1]))
            x_max = int(max(tr[0], br[0]))
            y_max = int(max(bl[1], br[1]))
            w, h = x_max - x_min, y_max - y_min

            sticker = Image.open(sticker_path).convert("RGBA").resize((w, h))
            img.paste(sticker, (x_min, y_min), sticker)

            output = io.BytesIO()
            img.save(output, format='JPEG')
            output.seek(0)
            return output
    except Exception as e:
        print(f"Xatolik: {e}")

    return None

if __name__ == '__main__':
    start_polling(dp, skip_updates=True)
