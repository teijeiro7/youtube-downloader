# Usar Python 3.11.9 oficial
FROM python:3.11.9-slim

# Establecer el directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema necesarias para yt-dlp y ffmpeg
RUN apt-get update && apt-get install -y \
    ffmpeg \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copiar archivos de requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el código de la aplicación
COPY main.py .

# Crear directorio temporal
RUN mkdir -p temp_downloads

# Exponer el puerto
EXPOSE $PORT

# Comando para ejecutar la aplicación
CMD uvicorn main:app --host 0.0.0.0 --port $PORT
