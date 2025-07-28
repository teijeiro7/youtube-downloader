# main.py
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel
import yt_dlp
import os
import tempfile
import uuid
from pathlib import Path
import asyncio
import aiofiles
import shutil
import ssl
import certifi
import re
import unicodedata
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

app = FastAPI(title="YouTube Downloader API", version="1.0.0")

# Middleware para logging de CORS
@app.middleware("http")
async def cors_logging_middleware(request: Request, call_next):
    origin = request.headers.get("origin")
    print(f"Request from origin: {origin}")
    print(f"Request method: {request.method}")
    print(f"Request URL: {request.url}")
    
    response = await call_next(request)
    
    print(f"Response headers: {response.headers}")
    return response

# Configurar CORS para permitir requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Permitir todos los orígenes temporalmente para debugging
    allow_credentials=False,  # Cambiar a False cuando allow_origins es "*"
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Crear directorio temporal para descargas
TEMP_DIR = Path("temp_downloads")
TEMP_DIR.mkdir(exist_ok=True)

class DownloadRequest(BaseModel):
    url: str
    format: str  # 'mp3' o 'mp4'
    quality: str = "high"  # Para MP3: 'low', 'medium', 'high', 'highest' | Para MP4: '720p', '1080p', '1440p', '2160p'

def clean_filename(filename: str) -> str:
    """Limpia el nombre del archivo para evitar caracteres problemáticos"""
    import re
    import unicodedata
    
    # Normalizar Unicode para manejar caracteres especiales
    filename = unicodedata.normalize('NFKD', filename)
    
    # Remover emojis y caracteres no ASCII
    cleaned = re.sub(r'[^\x00-\x7F]+', '', filename)
    
    # Remover caracteres especiales del sistema de archivos
    cleaned = re.sub(r'[<>:"/\\|?*]', '', cleaned)
    
    # Reemplazar espacios y caracteres problemáticos
    cleaned = cleaned.replace(' ', '_')
    cleaned = re.sub(r'[_]{2,}', '_', cleaned)  # Reducir múltiples guiones bajos
    
    # Limpiar inicio y final
    cleaned = cleaned.strip('_-.')
    
    # Si queda vacío, usar un nombre por defecto
    if not cleaned:
        cleaned = 'video'
    
    return cleaned[:100]  # Limitar longitud

def clean_youtube_url(url: str) -> str:
    """
    Limpia una URL de YouTube para extraer solo el video específico,
    removiendo parámetros de playlist, radio, etc.
    """
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        # Para URLs de YouTube, solo mantener el parámetro 'v' (video ID)
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            clean_params = {}
            
            # Mantener solo el video ID
            if 'v' in query_params:
                clean_params['v'] = query_params['v']
            
            # Para youtu.be URLs, mantener el path
            if 'youtu.be' in parsed.netloc:
                return f"https://www.youtube.com/watch?v={parsed.path[1:]}"
            
            # Reconstruir la URL limpia
            clean_query = urlencode(clean_params, doseq=True)
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                clean_query,
                None  # Remover fragment (#)
            ))
            
            return clean_url
        
        # Para otras URLs, devolver la original
        return url
        
    except Exception as e:
        print(f"Error limpiando URL: {e}")
        return url

async def download_video(url: str, format: str, quality: str, output_path: str) -> tuple[str, str]:
    """Descarga el video usando yt-dlp con calidad especificada"""
    
    # Limpiar la URL para evitar contenido de playlist/radio
    clean_url = clean_youtube_url(url)
    print(f"URL original: {url}")
    print(f"URL limpia: {clean_url}")
    
    # Configurar SSL
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    # Configuración base para yt-dlp
    base_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'no_warnings': False,
        'extractaudio': format == 'mp3',
        # Opciones SSL para macOS
        'nocheckcertificate': False,  # Vamos a intentar con certificados válidos primero
        'ignoreerrors': False,
    }
    
    if format == 'mp3':
        # Mapear calidades de audio
        audio_quality_map = {
            'low': '96',
            'medium': '128', 
            'high': '192',
            'highest': '320'
        }
        
        audio_quality = audio_quality_map.get(quality, '192')
        
        # Configuración para audio MP3
        ydl_opts = {
            **base_opts,
            'format': 'bestaudio/best',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': audio_quality,
            }],
        }
    else:
        # Mapear calidades de video usando los format IDs específicos de YouTube
        video_format_map = {
            '720p': 'best[height<=720][ext=mp4]/136/best[height<=720]',
            '1080p': 'best[height<=1080][height>=720][ext=mp4]/137/best[height<=1080]', 
            '1440p': 'best[height<=1440][height>=1080][ext=mp4]/271/400/best[height<=1440]',
            '2160p': 'best[height<=2160][height>=1440][ext=mp4]/313/401/best[height<=2160]'
        }
        
        video_format = video_format_map.get(quality, 'best[height<=1080][ext=mp4]/137/best[height<=1080]')
        
        # Configuración para video MP4
        ydl_opts = {
            **base_opts,
            'format': video_format,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
    
    try:
        # Primero extraer información sin filtros de formato
        info_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'no_warnings': False,
            'nocheckcertificate': False,
            'ignoreerrors': False,
        }
        
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            # Extraer información del video primero
            print(f"Intentando descargar en calidad: {quality}")
            print(f"Formato seleccionado: {ydl_opts.get('format', 'No especificado')}")
            
            info = ydl.extract_info(clean_url, download=False)
            title = info.get('title', 'video')
            clean_title = clean_filename(title)
            
            # Mostrar formatos disponibles para debugging
            if 'formats' in info:
                print("Formatos disponibles:")
                video_formats = [fmt for fmt in info['formats'] if fmt.get('vcodec') != 'none' and fmt.get('height')]
                for fmt in video_formats[:10]:  # Solo mostrar los primeros 10
                    height = fmt.get('height', 'N/A')
                    format_id = fmt.get('format_id', 'N/A')
                    ext = fmt.get('ext', 'N/A')
                    filesize = fmt.get('filesize', 'N/A')
                    print(f"  ID: {format_id}, Ext: {ext}, Height: {height}, Size: {filesize}")
            
            # Actualizar el template de salida con el título limpio
            ydl_opts['outtmpl'] = os.path.join(output_path, f'{clean_title}.%(ext)s')
            
            # Crear nueva instancia con la configuración actualizada
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                # Mostrar qué formato se va a descargar
                print(f"Intentando descargar con formato: {video_format if format != 'mp3' else 'audio'}")
                
                ydl_download.download([clean_url])
            
            # Encontrar el archivo descargado
            expected_ext = 'mp3' if format == 'mp3' else 'mp4'
            filename = f"{clean_title}.{expected_ext}"
            filepath = os.path.join(output_path, filename)
            
            # Verificar si el archivo existe, si no, buscar archivos en el directorio
            if not os.path.exists(filepath):
                print(f"Archivo esperado no encontrado: {filepath}")
                files = list(Path(output_path).glob(f"{clean_title}.*"))
                print(f"Archivos encontrados con el título: {files}")
                
                if files:
                    # Renombrar el archivo al formato esperado
                    original_file = files[0]
                    print(f"Renombrando {original_file} a {filepath}")
                    os.rename(original_file, filepath)
                else:
                    # Si no se encuentra, buscar cualquier archivo reciente
                    files = list(Path(output_path).glob("*"))
                    print(f"Todos los archivos en el directorio: {files}")
                    
                    if files:
                        # Tomar el archivo más reciente
                        latest_file = max(files, key=os.path.getctime)
                        print(f"Archivo más reciente: {latest_file}")
                        filename = f"{clean_title}.{expected_ext}"
                        filepath = os.path.join(output_path, filename)
                        print(f"Renombrando {latest_file} a {filepath}")
                        os.rename(latest_file, filepath)
                    else:
                        raise Exception(f"No se pudo encontrar el archivo descargado en {output_path}")
            
            print(f"Archivo final: {filepath}")
            return filepath, filename
            
    except Exception as e:
        print(f"Error en download_video: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=400, detail=f"Error al descargar: {str(e)}")

@app.get("/")
async def root():
    return {"message": "YouTube Downloader API funcionando correctamente"}

@app.get("/cors-test")
async def cors_test():
    """Endpoint para probar CORS"""
    return {
        "message": "CORS funcionando correctamente",
        "timestamp": "2025-07-28",
        "status": "success"
    }

@app.get("/qualities")
async def get_available_qualities():
    """Endpoint para obtener las calidades disponibles por formato"""
    return {
        "mp3": {
            "low": "96 kbps",
            "medium": "128 kbps", 
            "high": "192 kbps",
            "highest": "320 kbps"
        },
        "mp4": {
            "720p": "HD 720p",
            "1080p": "Full HD 1080p",
            "1440p": "2K 1440p", 
            "2160p": "4K 2160p"
        }
    }

@app.post("/inspect")
async def inspect_video_formats(request: dict):
    """Endpoint para inspeccionar los formatos disponibles de un video"""
    url = request.get('url')
    if not url:
        raise HTTPException(status_code=400, detail="URL es requerida")
    
    # Limpiar la URL para obtener información del video específico
    clean_url = clean_youtube_url(url)
    print(f"Inspeccionando - URL original: {url}")
    print(f"Inspeccionando - URL limpia: {clean_url}")
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': False,
            'noplaylist': True,  # Asegurar que no se procese como playlist
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            
            formats = []
            if 'formats' in info:
                for fmt in info['formats']:
                    if fmt.get('vcodec') != 'none':  # Solo formatos con video
                        formats.append({
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext'),
                            'resolution': f"{fmt.get('width', '?')}x{fmt.get('height', '?')}",
                            'height': fmt.get('height'),
                            'fps': fmt.get('fps'),
                            'filesize': fmt.get('filesize'),
                            'tbr': fmt.get('tbr'),  # Total bitrate
                            'vbr': fmt.get('vbr'),  # Video bitrate
                        })
            
            return {
                'title': info.get('title', ''),
                'duration': info.get('duration', 0),
                'formats': sorted(formats, key=lambda x: x.get('height', 0) or 0, reverse=True)
            }
            
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Error al inspeccionar video: {str(e)}")

@app.post("/download")
async def download_youtube_video(request: DownloadRequest):
    """Endpoint para descargar videos de YouTube"""
    
    if request.format not in ['mp3', 'mp4']:
        raise HTTPException(status_code=400, detail="Formato no válido. Usa 'mp3' o 'mp4'")
    
    # Validar calidades
    if request.format == 'mp3' and request.quality not in ['low', 'medium', 'high', 'highest']:
        raise HTTPException(status_code=400, detail="Calidad de audio no válida. Usa: 'low', 'medium', 'high', 'highest'")
    
    if request.format == 'mp4' and request.quality not in ['720p', '1080p', '1440p', '2160p']:
        raise HTTPException(status_code=400, detail="Calidad de video no válida. Usa: '720p', '1080p', '1440p', '2160p'")
    
    # Crear directorio temporal único para esta descarga
    download_id = str(uuid.uuid4())
    temp_path = TEMP_DIR / download_id
    temp_path.mkdir(exist_ok=True)
    
    try:
        # Descargar el video
        filepath, filename = await download_video(request.url, request.format, request.quality, str(temp_path))
        
        # Verificar que el archivo existe
        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="Error: el archivo no se generó correctamente")
        
        # Determinar el content type
        content_type = "audio/mpeg" if request.format == 'mp3' else "video/mp4"
        
        # Función para limpiar archivos después de la descarga
        async def cleanup():
            await asyncio.sleep(5)  # Esperar un poco antes de limpiar
            try:
                shutil.rmtree(temp_path)
            except:
                pass
        
        # Programar limpieza
        asyncio.create_task(cleanup())
        
        # Retornar el archivo
        return FileResponse(
            filepath,
            media_type=content_type,
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
        
    except HTTPException:
        # Limpiar en caso de error
        try:
            shutil.rmtree(temp_path)
        except:
            pass
        raise
    except Exception as e:
        # Limpiar en caso de error
        try:
            shutil.rmtree(temp_path)
        except:
            pass
        raise HTTPException(status_code=500, detail=f"Error interno del servidor: {str(e)}")

@app.get("/health")
async def health_check():
    """Endpoint para verificar el estado del servidor"""
    return {"status": "healthy", "message": "El servidor está funcionando correctamente"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)