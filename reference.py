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
REFERENCE_TEXT = []
REFERENCE_BBOX = None

def load_reference_plate():
    global REFERENCE_TEXT, REFERENCE_BBOX
    ref_img = cv2.imread(REFERENCE_IMAGE_PATH)
    results = reader.readtext(ref_img)
    for r in results:
        REFERENCE_TEXT.append(r[1].replace(" ", "").upper())
        if not REFERENCE_BBOX:
            REFERENCE_BBOX = r[0]

load_reference_plate()

user_photos = {}
user_states = {}

@dp.message_handler(commands=['start'])
async def start_command(message: types.Message):
    user_id = message.from_user.id
    user_states[user_id] = 'idle'
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📷 Rasm almashtirish"))
    await message.reply("Salom! Rasm yuborib, raqam ustiga logotip qo'yish uchun menyudan foydalaning.", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text == "📷 Rasm almashtirish")
async def ask_for_photo(message: types.Message):
    user_id = message.from_user.id
    if user_states.get(user_id) != 'idle':
        return
    user_states[user_id] = 'awaiting_photo'
    await message.reply("Iltimos, mashina rasmini yuboring.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def receive_photo(message: types.Message):
    user_id = message.from_user.id
    if user_states.get(user_id) != 'awaiting_photo':
        return

    photo = message.photo[-1]  # eng yuqori sifatli rasm
    photo_bytes = await photo.download(destination=io.BytesIO())
    photo_bytes.seek(0)
    user_photos[user_id] = photo_bytes.read()
    user_states[user_id] = 'awaiting_logo'

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for label in STICKERS:
        keyboard.add(KeyboardButton(label))

    await message.reply("Qaysi logotipni qo'yay?", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text in STICKERS)
async def apply_sticker(message: types.Message):
    user_id = message.from_user.id
    if user_states.get(user_id) != 'awaiting_logo' or user_id not in user_photos:
        return

    selected_sticker_path = STICKERS[message.text]
    result = overlay_sticker(user_photos[user_id], selected_sticker_path)

    if result:
        await message.reply_photo(photo=types.InputFile(result, filename='modified.jpg'))
    else:
        await message.reply("Raqamni topa olmadim. Original rasm:")
        await message.reply_photo(photo=types.InputFile(io.BytesIO(user_photos[user_id]), filename="original.jpg"))

    user_states[user_id] = 'idle'
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    keyboard.add(KeyboardButton("📷 Rasm almashtirish"))
    await message.reply("Yana logotip qo'yish uchun menyudan foydalaning.", reply_markup=keyboard)

@dp.message_handler()
async def fallback_handler(message: types.Message):
    await message.reply("Iltimos, menyudan foydalaning. /start buyrug'ini bosing.")

def overlay_sticker(image_bytes, sticker_path):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    gray = cv2.cvtColor(cv_img, cv2.COLOR_BGR2GRAY)
    blur = cv2.bilateralFilter(gray, 11, 17, 17)
    results = reader.readtext(cv_img)

    best_match = None
    best_ratio = 0

    for (bbox, text, prob) in results:
        candidate = text.replace(" ", "").upper()
        if len(candidate) >= 5 and any(char.isdigit() for char in candidate):
            ratio = max(
                SequenceMatcher(None, candidate, ref).ratio()
                for ref in REFERENCE_TEXT
            )
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = (bbox, candidate)

    if best_match and best_ratio > 0.4:
        (tl, tr, br, bl) = best_match[0]
        x_min = int(min(tl[0], bl[0]))
        y_min = int(min(tl[1], tr[1]))
        x_max = int(max(tr[0], br[0]))
        y_max = int(max(bl[1], br[1]))
        w, h = x_max - x_min, y_max - y_min

        sticker = Image.open(sticker_path).convert("RGBA").resize((w, h))
        img.paste(sticker, (x_min, y_min), sticker)

        output = io.BytesIO()
        img.save(output, format="JPEG")
        output.seek(0)
        return output

    return None

if __name__ == '__main__':
    start_polling(dp, skip_updates=True)
