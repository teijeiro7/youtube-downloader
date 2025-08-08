from fastapi import FastAPI, HTTPException, Request, Response
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

# Configurar CORS para permitir requests desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000", 
        "http://127.0.0.1:3000",
        "http://localhost:3001", 
        "http://127.0.0.1:3001",
        "https://*.vercel.app",
        "https://vercel.app",
        "https://*.onrender.com",
        "https://youtube-downloader-vercel.app",
        "https://youtube-downloader-a-mer-two.vercel.app",
        "https://rieljefe-youtube-downloader.vercel.app",
        "*"  # Temporal para debugging - remover en producción
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# Crear directorio temporal para descargas
TEMP_DIR = Path("temp_downloads")
TEMP_DIR.mkdir(exist_ok=True)

class DownloadRequest(BaseModel):
    url: str
    format: str  # 'mp3' o 'mp4'
    quality: str = "high"

def clean_filename(filename: str) -> str:
    """Limpia el nombre del archivo para evitar caracteres problemáticos"""
    filename = unicodedata.normalize('NFKD', filename)
    cleaned = re.sub(r'[^\x00-\x7F]+', '', filename)
    cleaned = re.sub(r'[<>:"/\\|?*]', '', cleaned)
    cleaned = cleaned.replace(' ', '_')
    cleaned = re.sub(r'[_]{2,}', '_', cleaned)
    cleaned = cleaned.strip('_-.')
    
    if not cleaned:
        cleaned = 'video'
    
    return cleaned[:100]

def clean_youtube_url(url: str) -> str:
    """Limpia una URL de YouTube para extraer solo el video específico"""
    try:
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        if 'youtube.com' in parsed.netloc or 'youtu.be' in parsed.netloc:
            clean_params = {}
            
            if 'v' in query_params:
                clean_params['v'] = query_params['v']
            
            if 'youtu.be' in parsed.netloc:
                return f"https://www.youtube.com/watch?v={parsed.path[1:]}"
            
            clean_query = urlencode(clean_params, doseq=True)
            clean_url = urlunparse((
                parsed.scheme,
                parsed.netloc,
                parsed.path,
                parsed.params,
                clean_query,
                None
            ))
            
            return clean_url
        
        return url
        
    except Exception as e:
        print(f"Error limpiando URL: {e}")
        return url

async def download_video(url: str, format: str, quality: str, output_path: str) -> tuple[str, str]:
    """Descarga el video usando yt-dlp con calidad especificada"""
    
    clean_url = clean_youtube_url(url)
    print(f"URL original: {url}")
    print(f"URL limpia: {clean_url}")
    
    ssl_context = ssl.create_default_context(cafile=certifi.where())
    
    base_opts = {
        'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
        'noplaylist': True,
        'no_warnings': False,
        'extractaudio': format == 'mp3',
        'nocheckcertificate': False,
        'ignoreerrors': False,
    }
    
    if format == 'mp3':
        audio_quality_map = {
            'low': '96',
            'medium': '128', 
            'high': '192',
            'highest': '320'
        }
        
        audio_quality = audio_quality_map.get(quality, '192')
        
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
        video_format_map = {
            '720p': 'best[height<=720][ext=mp4]/136/best[height<=720]',
            '1080p': 'best[height<=1080][height>=720][ext=mp4]/137/best[height<=1080]', 
            '1440p': 'best[height<=1440][height>=1080][ext=mp4]/271/400/best[height<=1440]',
            '2160p': 'best[height<=2160][height>=1440][ext=mp4]/313/401/best[height<=2160]'
        }
        
        video_format = video_format_map.get(quality, 'best[height<=1080][ext=mp4]/137/best[height<=1080]')
        
        ydl_opts = {
            **base_opts,
            'format': video_format,
            'postprocessors': [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4',
            }],
        }
    
    try:
        info_opts = {
            'outtmpl': os.path.join(output_path, '%(title)s.%(ext)s'),
            'noplaylist': True,
            'no_warnings': False,
            'nocheckcertificate': False,
            'ignoreerrors': False,
        }
        
        with yt_dlp.YoutubeDL(info_opts) as ydl:
            print(f"Intentando descargar en calidad: {quality}")
            print(f"Formato seleccionado: {ydl_opts.get('format', 'No especificado')}")
            
            info = ydl.extract_info(clean_url, download=False)
            title = info.get('title', 'video')
            clean_title = clean_filename(title)
            
            if 'formats' in info:
                print("Formatos disponibles:")
                video_formats = [fmt for fmt in info['formats'] if fmt.get('vcodec') != 'none' and fmt.get('height')]
                for fmt in video_formats[:10]:
                    height = fmt.get('height', 'N/A')
                    format_id = fmt.get('format_id', 'N/A')
                    ext = fmt.get('ext', 'N/A')
                    filesize = fmt.get('filesize', 'N/A')
                    print(f"  ID: {format_id}, Ext: {ext}, Height: {height}, Size: {filesize}")
            
            ydl_opts['outtmpl'] = os.path.join(output_path, f'{clean_title}.%(ext)s')
            
            with yt_dlp.YoutubeDL(ydl_opts) as ydl_download:
                print(f"Intentando descargar con formato: {video_format if format != 'mp3' else 'audio'}")
                ydl_download.download([clean_url])
            
            expected_ext = 'mp3' if format == 'mp3' else 'mp4'
            filename = f"{clean_title}.{expected_ext}"
            filepath = os.path.join(output_path, filename)
            
            if not os.path.exists(filepath):
                print(f"Archivo esperado no encontrado: {filepath}")
                files = list(Path(output_path).glob(f"{clean_title}.*"))
                print(f"Archivos encontrados con el título: {files}")
                
                if files:
                    original_file = files[0]
                    print(f"Renombrando {original_file} a {filepath}")
                    os.rename(original_file, filepath)
                else:
                    files = list(Path(output_path).glob("*"))
                    print(f"Todos los archivos en el directorio: {files}")
                    
                    if files:
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

# Manejar solicitudes OPTIONS para CORS
@app.options("/{path:path}")
async def options_handler(request: Request, path: str):
    """Maneja las solicitudes OPTIONS para CORS preflight"""
    return Response(
        status_code=200,
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
            "Access-Control-Allow-Headers": "*",
            "Access-Control-Max-Age": "86400"
        }
    )

@app.get("/")
async def root():
    return {"message": "YouTube Downloader API funcionando correctamente"}

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
    
    clean_url = clean_youtube_url(url)
    print(f"Inspeccionando - URL original: {url}")
    print(f"Inspeccionando - URL limpia: {clean_url}")
    
    try:
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'nocheckcertificate': False,
            'noplaylist': True,
        }
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(clean_url, download=False)
            
            formats = []
            if 'formats' in info:
                for fmt in info['formats']:
                    if fmt.get('vcodec') != 'none':
                        formats.append({
                            'format_id': fmt.get('format_id'),
                            'ext': fmt.get('ext'),
                            'resolution': f"{fmt.get('width', '?')}x{fmt.get('height', '?')}",
                            'height': fmt.get('height'),
                            'fps': fmt.get('fps'),
                            'filesize': fmt.get('filesize'),
                            'tbr': fmt.get('tbr'),
                            'vbr': fmt.get('vbr'),
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
    
    if request.format == 'mp3' and request.quality not in ['low', 'medium', 'high', 'highest']:
        raise HTTPException(status_code=400, detail="Calidad de audio no válida. Usa: 'low', 'medium', 'high', 'highest'")
    
    if request.format == 'mp4' and request.quality not in ['720p', '1080p', '1440p', '2160p']:
        raise HTTPException(status_code=400, detail="Calidad de video no válida. Usa: '720p', '1080p', '1440p', '2160p'")
    
    download_id = str(uuid.uuid4())
    temp_path = TEMP_DIR / download_id
    temp_path.mkdir(exist_ok=True)
    
    try:
        filepath, filename = await download_video(request.url, request.format, request.quality, str(temp_path))
        
        if not os.path.exists(filepath):
            raise HTTPException(status_code=500, detail="Error: el archivo no se generó correctamente")
        
        content_type = "audio/mpeg" if request.format == 'mp3' else "video/mp4"
        
        async def cleanup():
            await asyncio.sleep(5)
            try:
                shutil.rmtree(temp_path)
            except:
                pass
        
        asyncio.create_task(cleanup())
        
        return FileResponse(
            filepath,
            media_type=content_type,
            filename=filename,
            headers={"Content-Disposition": f"attachment; filename=\"{filename}\""}
        )
        
    except HTTPException:
        try:
            shutil.rmtree(temp_path)
        except:
            pass
        raise
    except Exception as e:
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
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
