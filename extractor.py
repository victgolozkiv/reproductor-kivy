import os
import random
import yt_dlp
import certifi
import time
from urllib.parse import quote

# Force certifi for Android SSL
os.environ['SSL_CERT_FILE'] = certifi.where()

class MyLogger:
    def debug(self, msg): pass
    def warning(self, msg): pass
    def error(self, msg): print(msg)

def get_audio_url(youtube_url, max_retries=3):
    """
    Extrae la URL de audio de un video de YouTube con reintentos automáticos.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'cachedir': False,
        'prefer_ffmpeg': False,
        'external_downloader': None,
        'postprocessors': [],
        'logger': MyLogger(),
        'noplaylist': True,
        'format_err': False,
        'socket_timeout': 15,
        'nocheckcertificate': True,
        'youtube_include_dash_manifest': True,
        'youtube_include_hls_manifest': True,
        'skip_unavailable_fragments': True,
        'retries': 5,
        'fragment_retries': 5,
    }
    
    for attempt in range(max_retries):
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                # Extract info without downloading
                info = ydl.extract_info(youtube_url, download=False)
                
                # Robust URL extraction from formats
                audio_url = None
                formats = info.get('formats', [])
                
                if not formats:
                    raise Exception("No formats available from video")
                
                # Helper to get bitrate safely
                def get_abr(f):
                    abr = f.get('abr') or f.get('tbr') or 0
                    return float(abr) if isinstance(abr, (int, float, str)) and str(abr).replace('.','',1).isdigit() else 0

                # Priority: audio-only format with highest bitrate
                audio_only = [f for f in formats if f.get('acodec') != 'none' and f.get('vcodec') == 'none']
                if audio_only:
                    audio_only.sort(key=get_abr, reverse=True)
                    audio_url = audio_only[0].get('url')
                
                # Fallback: best audio from any format
                if not audio_url:
                    audio_formats = [f for f in formats if f.get('acodec') != 'none']
                    if audio_formats:
                        audio_formats.sort(key=get_abr, reverse=True)
                        audio_url = audio_formats[0].get('url')
                
                # Last resort: url field
                if not audio_url:
                    audio_url = info.get('url')
                
                # Validate URL
                if not audio_url or not audio_url.startswith(('http://', 'https://')):
                    raise Exception(f"Invalid audio URL obtained: {audio_url[:50] if audio_url else 'None'}")
                
                title = info.get('title', 'Canción desconocida')
                thumbnail = info.get('thumbnail', '')
                artist = info.get('uploader') or info.get('channel') or "YouTube"
                
                print(f"✓ Audio URL extracted successfully on attempt {attempt + 1}")
                return audio_url, title, thumbnail, artist
                
        except Exception as e:
            error_msg = str(e)
            print(f"Attempt {attempt + 1}/{max_retries} failed: {error_msg[:100]}")
            
            # Si no hay más reintentos, retornar el error
            if attempt == max_retries - 1:
                print(f"✗ Final error after {max_retries} attempts: {error_msg}")
                return None, f"Error: {error_msg[:80]}", "", "Error"
            
            # Esperar antes de reintentar
            time.sleep(2 ** attempt)  # Backoff exponencial: 1s, 2s, 4s
    
    return None, "Unknown error occurred", "", "Error"

def search_youtube(query, limit=50):
    """
    Searches for videos on YouTube and returns a list of results.
    Raises exceptions on network/API errors so callers can classify them.
    """
    ydl_opts = {
        'format': 'bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'extract_flat': 'in_playlist',
        'prefer_ffmpeg': False,
        'external_downloader': None,
        'socket_timeout': 10,
    }
    
    search_query = f"ytsearch{limit}:{query}"
    results = []
    
    # Raises on error — caller handles the exception and shows the right toast
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(search_query, download=False)
        for entry in (info.get('entries') or []):
            if not entry:
                continue
            results.append({
                'id': entry.get('id'),
                'title': entry.get('title', 'Sin título'),
                'url': f"https://www.youtube.com/watch?v={entry.get('id')}",
                'thumbnail': entry.get('thumbnail', ''),
                'thumbnails': entry.get('thumbnails', []),
                'artist': entry.get('uploader') or entry.get('channel') or 'YouTube',
                'duration': entry.get('duration'),
            })
    
    print(f"search_youtube: found {len(results)} results for '{query}'")
    return results

def download_audio(youtube_url, save_dir):
    """
    Downloads audio from YouTube with Android-optimized settings.
    """
    from kivy.logger import Logger
    
    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'outtmpl': f'{save_dir}/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'noprogress': True,
        'cachedir': False,
        'prefer_ffmpeg': False,
        'postprocessors': [],
        'logger': MyLogger(),
        'noplaylist': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'no_color': True,
        'restrictfilenames': True,
        'windowsfilenames': True,
    }
    
    try:
        Logger.info(f"Extractor: Starting download {youtube_url[:30]}")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Ensure we are not using any dangerous post-processors
            ydl.download([youtube_url])
            return True, "Descarga exitosa"
    except Exception as e:
        Logger.error(f"Extractor: Download error: {e}")
        return False, str(e)

def get_recommendations():
    """
    Fetches a list of recommended/trending songs with a focus on global and popular hits.
    """
    global_seeds = [
        "Top 50 Global", "Billboard Hot 100", "Spotify Global Hits",
        "Today's Top Hits", "YouTube Music Trending", "Global Chart 2024",
        "Éxitos del momento", "Mejor música 2024"
    ]
    # Mix global hits with some variety
    query = random.choice(global_seeds)
    return search_youtube(query, limit=30)

if __name__ == "__main__":
    # Test
    test_results = get_recommendations()
    for res in test_results:
        print(f"- {res['title']} by {res['artist']}")
