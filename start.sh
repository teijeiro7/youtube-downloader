#!/bin/bash

# Script para iniciar YouTube Downloader (Backend + Frontend)
# Autor: GitHub Copilot
# Uso: ./start.sh

echo "🚀 Iniciando YouTube Downloader..."
echo "================================="

# Colores para el output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Función para limpiar procesos al salir
cleanup() {
    echo -e "\n${YELLOW}🛑 Deteniendo servicios...${NC}"
    if [ ! -z "$BACKEND_PID" ]; then
        kill $BACKEND_PID 2>/dev/null
        echo -e "${GREEN}✅ Backend detenido${NC}"
    fi
    if [ ! -z "$FRONTEND_PID" ]; then
        kill $FRONTEND_PID 2>/dev/null
        echo -e "${GREEN}✅ Frontend detenido${NC}"
    fi
    echo -e "${GREEN}🎉 YouTube Downloader detenido correctamente${NC}"
    exit 0
}

# Capturar señales para limpieza
trap cleanup SIGINT SIGTERM

# Verificar que estamos en el directorio correcto
if [ ! -f "requirements.txt" ] || [ ! -d "frontend" ] || [ ! -d "backend" ]; then
    echo -e "${RED}❌ Error: Ejecuta este script desde el directorio raíz del proyecto${NC}"
    exit 1
fi

# Verificar y detener procesos anteriores
echo -e "${YELLOW}🔍 Verificando procesos anteriores...${NC}"
if pgrep -f "uvicorn.*main:app" > /dev/null; then
    echo -e "${YELLOW}⚠️  Deteniendo backend anterior...${NC}"
    pkill -f "uvicorn.*main:app"
    sleep 2
fi

if pgrep -f "react-scripts start" > /dev/null; then
    echo -e "${YELLOW}⚠️  Deteniendo frontend anterior...${NC}"
    pkill -f "react-scripts start"
    sleep 2
fi

# Verificar que el entorno virtual existe
if [ ! -d "venv" ]; then
    echo -e "${RED}❌ Error: No se encontró el entorno virtual. Ejecuta: python -m venv venv${NC}"
    exit 1
fi

# Verificar que las dependencias del frontend están instaladas
if [ ! -d "frontend/node_modules" ]; then
    echo -e "${YELLOW}📦 Instalando dependencias del frontend...${NC}"
    cd frontend
    npm install
    cd ..
fi

echo -e "${BLUE}🔧 Configurando entorno...${NC}"

# Activar entorno virtual y configurar SSL
source venv/bin/activate
export SSL_CERT_FILE=$(python -m certifi)

echo -e "${GREEN}✅ Entorno virtual activado${NC}"
echo -e "${GREEN}✅ Certificados SSL configurados${NC}"

# Iniciar backend en segundo plano
echo -e "${BLUE}🖥️  Iniciando backend en puerto 8000...${NC}"
cd backend
uvicorn main:app --host 0.0.0.0 --port 8000 --reload > ../backend.log 2>&1 &
BACKEND_PID=$!
cd ..

# Esperar un momento para que el backend se inicie
sleep 3

# Verificar que el backend se inició correctamente
if ps -p $BACKEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Backend iniciado correctamente (PID: $BACKEND_PID)${NC}"
else
    echo -e "${RED}❌ Error al iniciar el backend${NC}"
    echo "Revisa el archivo backend.log para más detalles:"
    tail -10 backend.log
    exit 1
fi

# Iniciar frontend en segundo plano
echo -e "${BLUE}🌐 Iniciando frontend...${NC}"
cd frontend

# Configurar variables de entorno para que React use un puerto alternativo automáticamente
export BROWSER=none
export PORT=3001

npm start > ../frontend.log 2>&1 &
FRONTEND_PID=$!
cd ..

# Esperar un momento para que el frontend se inicie
sleep 5

# Verificar que el frontend se inició correctamente
if ps -p $FRONTEND_PID > /dev/null; then
    echo -e "${GREEN}✅ Frontend iniciado correctamente (PID: $FRONTEND_PID)${NC}"
else
    echo -e "${RED}❌ Error al iniciar el frontend${NC}"
    echo "Revisa el archivo frontend.log para más detalles:"
    tail -10 frontend.log
    cleanup
    exit 1
fi

echo ""
echo -e "${GREEN}🎉 YouTube Downloader iniciado correctamente!${NC}"
echo -e "${BLUE}📱 Frontend: ${NC}http://localhost:3001"
echo -e "${BLUE}🔗 Backend:  ${NC}http://localhost:8000"
echo -e "${BLUE}📋 API Docs: ${NC}http://localhost:8000/docs"
echo ""
echo -e "${YELLOW}💡 Presiona Ctrl+C para detener ambos servicios${NC}"
echo ""

# Mostrar logs en tiempo real
echo -e "${BLUE}📊 Logs en tiempo real:${NC}"
echo "========================"

# Función para mostrar logs alternados
show_logs() {
    while true; do
        if [ -f "backend.log" ]; then
            echo -e "${BLUE}[BACKEND]${NC} $(tail -1 backend.log 2>/dev/null)"
        fi
        if [ -f "frontend.log" ]; then
            echo -e "${GREEN}[FRONTEND]${NC} $(tail -1 frontend.log 2>/dev/null)"
        fi
        sleep 2
    done
}

# Mantener el script corriendo y mostrar logs
while true; do
    # Verificar que ambos procesos siguen corriendo
    if ! ps -p $BACKEND_PID > /dev/null; then
        echo -e "${RED}❌ El backend se ha detenido inesperadamente${NC}"
        cleanup
        exit 1
    fi
    
    if ! ps -p $FRONTEND_PID > /dev/null; then
        echo -e "${RED}❌ El frontend se ha detenido inesperadamente${NC}"
        cleanup
        exit 1
    fi
    
    sleep 5
done
