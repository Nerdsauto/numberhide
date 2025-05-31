FROM python:3.10-slim

# 📦 OpenCV va EasyOCR uchun kerakli grafik kutubxonalarni o‘rnatish
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 📁 Ishchi papka
WORKDIR /app

# 📂 Loyihani konteynerga ko‘chirish
COPY . /app

# 🐍 Python kutubxonalarni o‘rnatish
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 🚀 Botni ishga tushirish
CMD ["python", "reference.py"]
