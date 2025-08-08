import React, { useState } from 'react';
import { Download, Music, Video, AlertCircle, CheckCircle2, Loader2 } from 'lucide-react';

export default function YouTubeDownloader() {
  const [url, setUrl] = useState('');
  const [format, setFormat] = useState('mp4');
  const [quality, setQuality] = useState('1080p');
  const [isLoading, setIsLoading] = useState(false);
  const [message, setMessage] = useState('');
  const [messageType, setMessageType] = useState('');

  // Opciones de calidad por formato
  const qualityOptions = {
    mp3: {
      low: '96 kbps',
      medium: '128 kbps',
      high: '192 kbps',
      highest: '320 kbps'
    },
    mp4: {
      '720p': 'HD 720p',
      '1080p': 'Full HD 1080p',
      '1440p': '2K 1440p',
      '2160p': '4K 2160p'
    }
  };

  const isValidYouTubeUrl = (url) => {
    const youtubeRegex = /^(https?:\/\/)?(www\.)?(youtube\.com\/(watch\?v=|embed\/|v\/)|youtu\.be\/)[\w-]+/;
    return youtubeRegex.test(url);
  };

  const handleFormatChange = (newFormat) => {
    setFormat(newFormat);
    // Cambiar calidad por defecto según el formato
    if (newFormat === 'mp3') {
      setQuality('high');
    } else {
      setQuality('1080p');
    }
  };

  const handleDownload = async () => {
    if (!url.trim()) {
      setMessage('Por favor, ingresa una URL de YouTube');
      setMessageType('error');
      return;
    }

    if (!isValidYouTubeUrl(url)) {
      setMessage('Por favor, ingresa una URL válida de YouTube');
      setMessageType('error');
      return;
    }

    setIsLoading(true);
    setMessage('');

    try {
      const apiUrl = process.env.REACT_APP_API_URL || 'http://localhost:8000';
      console.log('API URL:', apiUrl); // Para debugging
      
      const response = await fetch(`${apiUrl}/download`, {
        method: 'POST',
        mode: 'cors',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/octet-stream',
          'Access-Control-Allow-Origin': '*',
        },
        body: JSON.stringify({
          url: url,
          format: format,
          quality: quality
        })
      });

      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`Error en el servidor: ${response.status} - ${errorText}`);
      }

      const blob = await response.blob();
      const downloadUrl = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = downloadUrl;
      
      // Obtener el nombre del archivo desde los headers de respuesta
      const contentDisposition = response.headers.get('content-disposition');
      let filename = `video.${format}`;
      if (contentDisposition) {
        const filenameMatch = contentDisposition.match(/filename="(.+)"/);
        if (filenameMatch) {
          filename = filenameMatch[1];
        }
      }
      
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(downloadUrl);

      setMessage('¡Descarga completada exitosamente!');
      setMessageType('success');
    } catch (error) {
      setMessage('Error al descargar el video. Verifica la URL e intenta nuevamente.');
      setMessageType('error');
    } finally {
      setIsLoading(false);
    }
  };

  const handleUrlChange = (e) => {
    setUrl(e.target.value);
    if (message) {
      setMessage('');
      setMessageType('');
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-50 to-slate-100 py-12 px-4">
      <div className="max-w-2xl mx-auto">
        {/* Header */}
        <div className="text-center mb-12">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-red-500 rounded-full mb-4">
            <Download className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-4xl font-bold text-slate-800 mb-2">
            YouTube Downloader
          </h1>
          <p className="text-slate-600 text-lg">
            Descarga videos de YouTube en formato MP3 o MP4
          </p>
        </div>

        {/* Main Card */}
        <div className="bg-white rounded-2xl shadow-xl p-8 border border-slate-200">
          {/* URL Input */}
          <div className="mb-6">
            <label htmlFor="url" className="block text-sm font-medium text-slate-700 mb-2">
              URL del video de YouTube
            </label>
            <input
              type="url"
              id="url"
              value={url}
              onChange={handleUrlChange}
              placeholder="https://www.youtube.com/watch?v=..."
              className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none transition-all duration-200 text-slate-700"
              disabled={isLoading}
            />
          </div>

          {/* Format Selection */}
          <div className="mb-8">
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Formato de descarga
            </label>
            <div className="grid grid-cols-2 gap-4">
              <button
                onClick={() => handleFormatChange('mp4')}
                disabled={isLoading}
                className={`p-4 rounded-lg border-2 transition-all duration-200 ${
                  format === 'mp4'
                    ? 'border-red-500 bg-red-50 text-red-700'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                <Video className="w-6 h-6 mx-auto mb-2" />
                <div className="font-medium">MP4</div>
                <div className="text-sm opacity-75">Video completo</div>
              </button>
              
              <button
                onClick={() => handleFormatChange('mp3')}
                disabled={isLoading}
                className={`p-4 rounded-lg border-2 transition-all duration-200 ${
                  format === 'mp3'
                    ? 'border-red-500 bg-red-50 text-red-700'
                    : 'border-slate-200 bg-white text-slate-600 hover:border-slate-300'
                } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                <Music className="w-6 h-6 mx-auto mb-2" />
                <div className="font-medium">MP3</div>
                <div className="text-sm opacity-75">Solo audio</div>
              </button>
            </div>
          </div>

          {/* Quality Selection */}
          <div className="mb-8">
            <label className="block text-sm font-medium text-slate-700 mb-3">
              Calidad de {format === 'mp3' ? 'audio' : 'video'}
            </label>
            <select
              value={quality}
              onChange={(e) => setQuality(e.target.value)}
              disabled={isLoading}
              className="w-full px-4 py-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-red-500 focus:border-transparent outline-none transition-all duration-200 text-slate-700 bg-white"
            >
              {Object.entries(qualityOptions[format]).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
          </div>

          {/* Download Button */}
          <button
            onClick={handleDownload}
            disabled={isLoading || !url.trim()}
            className="w-full bg-red-500 hover:bg-red-600 disabled:bg-slate-300 disabled:cursor-not-allowed text-white font-medium py-3 px-6 rounded-lg transition-all duration-200 flex items-center justify-center gap-2"
          >
            {isLoading ? (
              <>
                <Loader2 className="w-5 h-5 animate-spin" />
                Descargando...
              </>
            ) : (
              <>
                <Download className="w-5 h-5" />
                Descargar {format.toUpperCase()} ({qualityOptions[format][quality]})
              </>
            )}
          </button>

          {/* Message */}
          {message && (
            <div className={`mt-4 p-4 rounded-lg flex items-center gap-2 ${
              messageType === 'error' 
                ? 'bg-red-50 text-red-700 border border-red-200' 
                : 'bg-green-50 text-green-700 border border-green-200'
            }`}>
              {messageType === 'error' ? (
                <AlertCircle className="w-5 h-5 flex-shrink-0" />
              ) : (
                <CheckCircle2 className="w-5 h-5 flex-shrink-0" />
              )}
              <span>{message}</span>
            </div>
          )}
        </div>

        {/* Instructions */}
        <div className="mt-8 bg-white rounded-xl p-6 border border-slate-200">
          <h3 className="font-semibold text-slate-800 mb-3">Instrucciones de uso:</h3>
          <ol className="text-slate-600 space-y-2 text-sm">
            <li className="flex items-start gap-2">
              <span className="bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">1</span>
              Copia la URL del video de YouTube que deseas descargar
            </li>
            <li className="flex items-start gap-2">
              <span className="bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">2</span>
              Pégala en el campo de URL arriba
            </li>
            <li className="flex items-start gap-2">
              <span className="bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">3</span>
              Selecciona el formato deseado (MP4 para video o MP3 para audio)
            </li>
            <li className="flex items-start gap-2">
              <span className="bg-red-500 text-white text-xs rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5">4</span>
              Haz clic en "Descargar" y espera a que se complete la descarga
            </li>
          </ol>
        </div>

        {/* Footer */}
        <div className="text-center mt-8 text-slate-500 text-sm">
          <p>Respeta los derechos de autor y las políticas de YouTube</p>
        </div>
      </div>
    </div>
  );
}