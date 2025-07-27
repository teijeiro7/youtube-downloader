#!/bin/bash

# Script para detener YouTube Downloader
# Autor: GitHub Copilot
# Uso: ./stop.sh

echo "🛑 Deteniendo YouTube Downloader..."

# Colores
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Detener procesos del backend
echo -e "${YELLOW}🔍 Buscando procesos del backend...${NC}"
BACKEND_PIDS=$(ps aux | grep "uvicorn.*backend.main:app" | grep -v grep | awk '{print $2}')
if [ ! -z "$BACKEND_PIDS" ]; then
    echo -e "${YELLOW}🛑 Deteniendo backend (PIDs: $BACKEND_PIDS)...${NC}"
    echo $BACKEND_PIDS | xargs kill -TERM 2>/dev/null
    sleep 2
    # Forzar si es necesario
    echo $BACKEND_PIDS | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✅ Backend detenido${NC}"
else
    echo -e "${GREEN}✅ No hay procesos del backend ejecutándose${NC}"
fi

# Detener procesos del frontend
echo -e "${YELLOW}🔍 Buscando procesos del frontend...${NC}"
FRONTEND_PIDS=$(ps aux | grep "react-scripts start" | grep -v grep | awk '{print $2}')
if [ ! -z "$FRONTEND_PIDS" ]; then
    echo -e "${YELLOW}🛑 Deteniendo frontend (PIDs: $FRONTEND_PIDS)...${NC}"
    echo $FRONTEND_PIDS | xargs kill -TERM 2>/dev/null
    sleep 2
    # Forzar si es necesario
    echo $FRONTEND_PIDS | xargs kill -9 2>/dev/null
    echo -e "${GREEN}✅ Frontend detenido${NC}"
else
    echo -e "${GREEN}✅ No hay procesos del frontend ejecutándose${NC}"
fi

# Limpiar archivos de log
if [ -f "backend.log" ]; then
    rm backend.log
    echo -e "${GREEN}✅ Log del backend limpiado${NC}"
fi

if [ -f "frontend.log" ]; then
    rm frontend.log
    echo -e "${GREEN}✅ Log del frontend limpiado${NC}"
fi

echo -e "${GREEN}🎉 YouTube Downloader detenido correctamente${NC}"
