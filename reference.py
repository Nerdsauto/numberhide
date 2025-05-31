import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.utils.executor import start_polling
from PIL import Image
import easyocr
import cv2
import numpy as np
import io
from difflib import SequenceMatcher
from dotenv import load_dotenv

load_dotenv()  # .env fayldan tokenni olish uchun

API_TOKEN = os.getenv("API_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

reader = easyocr.Reader(['en'])

# Logotip fayllari
STICKERS = {
    "Real Auto": "Real.png",
    "Nerds Auto": "Nerds.png",
    "Jalil Auto": "Jalil.png"
}

REFERENCE_IMAGE_PATH = "reference_plate.jpeg"
REFERENCE_TEXT = "01","10","20","25","30","40","50","60","70","75","80","85","90","95","01A123BC"
REFERENCE_BBOX = None

# OCR orqali raqamni yuklash
def load_reference_plate():
    global REFERENCE_TEXT, REFERENCE_BBOX
    ref_img = cv2.imread(REFERENCE_IMAGE_PATH)
    results = reader.readtext(ref_img)
    if results:
        REFERENCE_TEXT = results[0][1].replace(" ", "").upper()
        REFERENCE_BBOX = results[0][0]

load_reference_plate()

user_photos = {}
user_selected_sticker = {}

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    await message.reply("Salom! Mashina rasmini tashlang. Logotipni yopib beraman.")

@dp.message_handler(content_types=types.ContentType.PHOTO)
async def receive_photo(message: types.Message):
    user_id = message.from_user.id
    photo = message.photo[-1]
    photo_bytes = await photo.download(destination=io.BytesIO())
    photo_bytes.seek(0)
    user_photos[user_id] = photo_bytes.read()

    keyboard = ReplyKeyboardMarkup(resize_keyboard=True)
    for label in STICKERS.keys():
        keyboard.add(KeyboardButton(label))

    await message.reply("Qaysi logotipni qo'yay?", reply_markup=keyboard)

@dp.message_handler(lambda message: message.text in STICKERS)
async def apply_sticker(message: types.Message):
    user_id = message.from_user.id
    if user_id not in user_photos:
        await message.reply("Iltimos, avval mashina rasmini yuboring.")
        return

    selected_sticker_path = STICKERS[message.text]
    result = overlay_sticker(user_photos[user_id], selected_sticker_path)

    if result is None:
        await message.reply("Raqamni topa olmadim. Original rasm:")
        await message.reply_photo(photo=types.InputFile(io.BytesIO(user_photos[user_id]), filename="original.jpg"))
    else:
        await message.reply_photo(photo=types.InputFile(result, filename='modified.jpg'))

    await message.reply("Yana bormi, ustoz? 😎")

def overlay_sticker(image_bytes, sticker_path):
    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    cv_img = cv2.cvtColor(np.array(img), cv2.COLOR_RGB2BGR)

    results = reader.readtext(cv_img)
    best_match = None
    best_ratio = 0.0

    for (bbox, text, prob) in results:
        candidate = text.replace(" ", "").upper()
        ratio = SequenceMatcher(None, candidate, "".join(REFERENCE_TEXT)).ratio()
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

    return None

if __name__ == '__main__':
    start_polling(dp, skip_updates=True)
