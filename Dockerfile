FROM python:3.10-slim

# 📦 Kutubxonalarni o‘rnatish
RUN apt-get update && apt-get install -y \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    && rm -rf /var/lib/apt/lists/*

# 🔐 BOT TOKENNI BERISH
ENV API_TOKEN=7860498028:AAGV8cOHchdvyG9RVKUZDYIqi-Pr5oz9R-4

# 📁 Ishchi katalog
WORKDIR /app

# 📂 Fayllarni konteynerga o‘tkazish
COPY . /app

# 📦 Kutubxonalarni o‘rnatish
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# 🚀 Botni ishga tushirish
CMD ["python", "reference.py"]
