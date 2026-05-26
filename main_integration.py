# INTEGRACIÓN PARA MAIN.PY - Agregar estas funciones y modificaciones a tu archivo main.py existente

# 1. IMPORTS (agregar al inicio del archivo después de los imports existentes)
from kivy_search_engine import KivySearchEngine, SearchResult
from kivy_recommendation_system import KivyRecommendationSystem, Recommendation
import hashlib
import uuid

# 2. MODIFICAR EL __init__ DE MusicPlayerApp (agregar después de la línea 526 aproximadamente)

def __init__(self, **kwargs):
    super().__init__(**kwargs)
    try:
        self.player = None # Lazy initialization in on_start
    except Exception as e:
        print(f"Error initializing player: {e}")
        self.player = None
    self.update_event = None
    self.pulse_anim = None
    
    # Optimization: Thread Pool & Cache
    self.executor = ThreadPoolExecutor(max_workers=4)
    self.url_cache = {}    # {video_id: (url, title, thumb, artist, timestamp)}
    self.thumb_cache = {}  # {url: local_path or Image}
    self.pre_fetched_id = None
    
    # Audio State
    self.album_scale = 1.0 
    self.title_glow = 1.0  
    
    # Pre-initialize pulse_anim to avoid NoneType errors
    self._init_animations()
    
    # State management
    self.current_playlist = []
    self.current_index = -1
    self.current_playlist_name = ""
    self.last_results = []
    self.recommendations_cache = []
    self.search_history = []
    self.is_local_playback = False
    
    # NUEVO: Sistema de búsqueda y recomendaciones optimizado
    self.search_engine = None
    self.recommendation_system = None
    self.user_id = None
    self.next_songs_queue = []
    self.db_path = os.path.join(self.user_data_dir, 'music_optimized.db')
    
    # Initial playlist load in background to avoid ANR at startup
    self.playlists = {}
    threading.Thread(target=self._load_playlists_async, daemon=True).start()
    
    # Folder Path Management - Deferred to on_start for ANR prevention
    self.music_path = ""
    
    self.file_manager = MDFileManager(
        exit_manager=self.exit_manager,
        select_path=self.select_path,
    )
    self.manager_open = False

# 3. MODIFICAR on_start (agregar después de la línea 820 aproximadamente)

def on_start(self):
    """Initialization after app is fully built"""
    # 1. Initialize Paths & Storage
    self._init_music_path()
    
    # 2. Initialize player here to ensure Android Activity is ready
    if not self.player:
        from player import get_best_player
        self.player = get_best_player()
        Logger.info("App: Audio engine initialized in on_start")

    # NUEVO: Inicializar sistema de búsqueda y recomendaciones
    self._init_search_recommendation_system()

    if platform == "android":
         # 3. Request permissions & Start Service
        self._setup_media_receiver()
        self._request_android_permissions()
    
    # 4. Load recommendations in background thread
    threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()

# 4. AGREGAR NUEVAS FUNCIONES (agregar estas funciones nuevas a tu main.py)

def _init_search_recommendation_system(self):
    """Inicializar el sistema optimizado de búsqueda y recomendaciones"""
    try:
        # Generar ID único para el usuario
        self.user_id = self._get_or_create_user_id()
        
        # Inicializar motores
        self.search_engine = KivySearchEngine(self.db_path, self)
        self.recommendation_system = KivyRecommendationSystem(self.db_path, self)
        
        Logger.info("App: Sistema de búsqueda y recomendaciones inicializado")
        
        # Cargar recomendaciones iniciales
        self._load_initial_recommendations()
        
    except Exception as e:
        Logger.error(f"App: Error inicializando sistema de búsqueda: {e}")

def _get_or_create_user_id(self):
    """Obtener o crear ID único de usuario"""
    user_id_file = os.path.join(self.user_data_dir, 'user_id.txt')
    
    if os.path.exists(user_id_file):
        try:
            with open(user_id_file, 'r') as f:
                return f.read().strip()
        except:
            pass
    
    # Crear nuevo ID
    import uuid
    user_id = str(uuid.uuid4())
    
    try:
        with open(user_id_file, 'w') as f:
            f.write(user_id)
    except:
        pass
    
    return user_id

def _load_initial_recommendations(self):
    """Cargar recomendaciones iniciales en segundo plano"""
    def _load():
        try:
            if self.recommendation_system:
                self.recommendation_system.get_recommendations_async(
                    self.user_id, 20, 'home',
                    callback=self._on_initial_recommendations_loaded
                )
        except Exception as e:
            Logger.error(f"App: Error cargando recomendaciones iniciales: {e}")
    
    threading.Thread(target=_load, daemon=True).start()

def _on_initial_recommendations_loaded(self, recommendations):
    """Callback cuando las recomendaciones iniciales están listas"""
    try:
        if recommendations:
            self.recommendations_cache = recommendations
            # Actualizar UI si estamos en la pantalla principal
            if self.root.current == 'library' and self.library_mode == 'recommendations':
                self._update_results_rv_recommendations(recommendations)
            Logger.info(f"App: {len(recommendations)} recomendaciones iniciales cargadas")
    except Exception as e:
        Logger.error(f"App: Error procesando recomendaciones iniciales: {e}")

# 5. REEMPLAZAR search_songs (modificar tu función existente)

def search_songs(self, query):
    """Búsqueda optimizada con Query Expansion y Fuzzy Search"""
    if not query or not query.strip():
        return
    
    # Mostrar spinner
    self.root.get_screen("library").ids.search_spinner.active = True
    self.root.get_screen("library").ids.list_header.text = "BUSCANDO..."
    
    # Búsqueda asíncrona
    if self.search_engine:
        self.search_engine.search_songs_async(
            query, 20, self.user_id,
            callback=self._on_search_results_loaded
        )
    else:
        # Fallback a búsqueda original
        self._search_songs_fallback(query)

def _on_search_results_loaded(self, results):
    """Callback cuando los resultados de búsqueda están listos"""
    try:
        # Ocultar spinner
        self.root.get_screen("library").ids.search_spinner.active = False
        
        if results:
            self.last_results = results
            self.library_mode = 'search'
            self.root.get_screen("library").ids.list_header.text = f"RESULTADOS ({len(results)})"
            
            # Convertir a formato para RecycleView
            rv_data = []
            for i, result in enumerate(results):
                rv_data.append({
                    'title': result.title,
                    'artist': result.artist,
                    'thumbnail': result.thumbnail_url,
                    'song_data': {
                        'url': result.youtube_url,
                        'title': result.title,
                        'artist': result.artist,
                        'thumbnail': result.thumbnail_url,
                        'song_id': result.song_id
                    }
                })
            
            self._update_results_rv(rv_data)
            
            # Actualizar interacción del usuario
            if self.search_engine and self.user_id:
                self.search_engine.update_user_interaction(self.user_id, 'search', query)
                
        else:
            self.root.get_screen("library").ids.list_header.text = "SIN RESULTADOS"
            self._update_results_rv([])
            
    except Exception as e:
        Logger.error(f"App: Error procesando resultados de búsqueda: {e}")
        self.root.get_screen("library").ids.search_spinner.active = False

def _update_results_rv_recommendations(self, recommendations):
    """Actualizar RecycleView con recomendaciones"""
    try:
        rv_data = []
        for i, rec in enumerate(recommendations):
            rv_data.append({
                'title': rec.title,
                'artist': rec.artist,
                'thumbnail': rec.thumbnail_url,
                'song_data': {
                    'url': rec.youtube_url,
                    'title': rec.title,
                    'artist': rec.artist,
                    'thumbnail': rec.thumbnail_url,
                    'song_id': rec.song_id,
                    'reason': rec.reason
                }
            })
        
        self._update_results_rv(rv_data)
        
    except Exception as e:
        Logger.error(f"App: Error actualizando recomendaciones: {e}")

# 6. MODIFICAR play_selected_song (agregar después de tu función existente)

def play_selected_song(self, index):
    """Reproducir canción seleccionada con sistema de recomendaciones"""
    try:
        # Tu código existente para reproducir la canción
        song_data = self.last_results[index]['song_data'] if self.library_mode == 'search' else self.recommendations_cache[index].song_data
        
        # ... (tu código existente para reproducir) ...
        
        # NUEVO: Actualizar sistema de recomendaciones
        if self.recommendation_system and self.user_id:
            song_id = song_data.get('song_id')
            if song_id:
                # Actualizar interacción
                self.recommendation_system.update_user_profile_async(
                    self.user_id, song_id, 'play'
                )
                
                # Obtener siguientes canciones recomendadas
                self.recommendation_system.get_next_recommendations_async(
                    self.user_id, song_id, 5,
                    callback=self._on_next_songs_ready
                )
        
        # NUEVO: Agregar canción a la base de datos local si no existe
        if self.search_engine and song_data:
            self.search_engine.add_song_from_youtube(
                song_data.get('title', ''),
                song_data.get('artist', ''),
                song_data.get('url', ''),
                song_data.get('thumbnail', '')
            )
            
    except Exception as e:
        Logger.error(f"App: Error en play_selected_song: {e}")

def _on_next_songs_ready(self, next_songs):
    """Callback cuando las siguientes canciones están listas"""
    try:
        self.next_songs_queue = next_songs
        Logger.info(f"App: {len(next_songs)} siguientes canciones listas")
        
        # Opcional: mostrar notificación o actualizar UI
        if next_songs:
            next_song = next_songs[0]
            Logger.info(f"App: Siguiente recomendada: {next_song.title} - {next_song.reason}")
            
    except Exception as e:
        Logger.error(f"App: Error procesando siguientes canciones: {e}")

# 7. MODIFICAR on_next (agregar lógica de cola inteligente)

def on_next(self):
    """Siguiente canción con cola inteligente"""
    try:
        # Si hay canciones en la cola de recomendaciones, usar la primera
        if self.next_songs_queue:
            next_song = self.next_songs_queue.pop(0)
            
            # Convertir a formato de song_data
            song_data = {
                'url': next_song.youtube_url,
                'title': next_song.title,
                'artist': next_song.artist,
                'thumbnail': next_song.thumbnail_url,
                'song_id': next_song.song_id
            }
            
            # Reproducir siguiente canción recomendada
            self._play_song_data(song_data)
            
            # Actualizar interacción
            if self.recommendation_system and self.user_id:
                self.recommendation_system.update_user_profile_async(
                    self.user_id, next_song.song_id, 'play'
                )
                
                # Obtener más siguientes canciones
                self.recommendation_system.get_next_recommendations_async(
                    self.user_id, next_song.song_id, 3,
                    callback=self._on_next_songs_ready
                )
            
            Logger.info(f"App: Reproduciendo siguiente recomendada: {next_song.title}")
            return
        
        # Si no hay canciones en cola, usar el comportamiento normal
        # ... (tu código existente para on_next) ...
        
    except Exception as e:
        Logger.error(f"App: Error en on_next: {e}")

def _play_song_data(self, song_data):
    """Función helper para reproducir song_data"""
    try:
        # Obtener URL de audio
        from extractor import get_audio_url
        audio_url, title, thumb, artist = get_audio_url(song_data['url'])
        
        if audio_url:
            # Reproducir con tu player existente
            self.player.play(audio_url)
            
            # Actualizar UI
            self._update_player_ui(title, artist, thumb)
            
            # Actualizar canción actual
            self.current_song_data = song_data
            
        else:
            toast("Error obteniendo audio")
            
    except Exception as e:
        Logger.error(f"App: Error reproduciendo canción: {e}")
        toast("Error reproduciendo")

def _update_player_ui(self, title, artist, thumbnail):
    """Actualizar UI del reproductor"""
    try:
        player_screen = self.root.get_screen("player")
        player_screen.ids.song_title.text = title
        player_screen.ids.artist_name.text = artist
        player_screen.ids.thumbnail.source = thumbnail
        
        # Actualizar notificación si es Android
        if platform == "android":
            self._update_notification(title, artist)
            
    except Exception as e:
        Logger.error(f"App: Error actualizando UI: {e}")

# 8. AGREGAR FUNCIÓN DE CLEANUP (modificar on_stop)

def on_stop(self):
    """Purge memory and release resources on exit"""
    try:
        self._cancel_update_event()
        if self.player:
            self.player.stop()
        
        # NUEVO: Cerrar sistemas de búsqueda y recomendaciones
        if self.search_engine:
            self.search_engine.close()
        if self.recommendation_system:
            self.recommendation_system.close()
        
        # Aggressive cache clearing for Android stability
        from kivy.cache import Cache
        Cache.remove('kv.image')
        Cache.remove('kv.texture')
        
        # Explicit garbage collection
        gc.collect()
        Logger.info("App: Memory purged and resources released")
    except Exception as e:
        Logger.warning(f"App: Error in on_stop: {e}")

# 9. MODIFICAR _fetch_recommendations_thread (actualizar tu función existente)

def _fetch_recommendations_thread(self):
    """Cargar recomendaciones optimizadas en segundo plano"""
    try:
        if self.recommendation_system:
            recommendations = self.recommendation_system.get_recommendations(
                self.user_id, 20, 'home'
            )
            
            if recommendations:
                self.recommendations_cache = recommendations
                
                # Actualizar UI en el main thread
                Clock.schedule_once(lambda dt: self._on_initial_recommendations_loaded(recommendations))
        else:
            # Fallback a recomendaciones originales
            from extractor import get_recommendations
            original_recs = get_recommendations()
            # Convertir formato original a nuevo sistema si es necesario
            
    except Exception as e:
        Logger.error(f"App: Error en _fetch_recommendations_thread: {e}")

# 10. NUEVAS FUNCIONES DE UTILIDAD

def get_user_recommendations(self, context='general'):
    """Obtener recomendaciones para el usuario actual"""
    try:
        if self.recommendation_system:
            return self.recommendation_system.get_recommendations(
                self.user_id, 20, context
            )
        return []
    except Exception as e:
        Logger.error(f"App: Error obteniendo recomendaciones: {e}")
        return []

def search_artist_songs(self, artist_id):
    """Buscar todas las canciones de un artista"""
    try:
        if self.search_engine:
            results = self.search_engine.get_artist_songs(artist_id, 20)
            
            # Convertir a formato para UI
            rv_data = []
            for result in results:
                rv_data.append({
                    'title': result.title,
                    'artist': result.artist,
                    'thumbnail': result.thumbnail_url,
                    'song_data': {
                        'url': result.youtube_url,
                        'title': result.title,
                        'artist': result.artist,
                        'thumbnail': result.thumbnail_url,
                        'song_id': result.song_id
                    }
                })
            
            return rv_data
        return []
    except Exception as e:
        Logger.error(f"App: Error buscando canciones del artista: {e}")
        return []

def update_user_preferences(self, interaction_type='play'):
    """Actualizar preferencias del usuario basado en interacción actual"""
    try:
        if self.recommendation_system and self.user_id and hasattr(self, 'current_song_data'):
            song_id = self.current_song_data.get('song_id')
            if song_id:
                self.recommendation_system.update_user_profile_async(
                    self.user_id, song_id, interaction_type
                )
    except Exception as e:
        Logger.error(f"App: Error actualizando preferencias: {e}")

# EJEMPLO DE USO EN TU UI:

# Para agregar un botón de "Más de este artista":
def on_artist_click(self, artist_name, artist_id):
    """Cuando el usuario hace click en un artista"""
    results = self.search_artist_songs(artist_id)
    if results:
        self.last_results = results
        self.library_mode = 'artist'
        self.root.get_screen("library").ids.list_header.text = f"MÁS DE {artist_name.upper()}"
        self._update_results_rv(results)
        self.root.current = 'library'

# Para agregar botón de "Me gusta":
def on_like_song(self):
    """Cuando el usuario da like a una canción"""
    self.update_user_preferences('like')
    toast("¡Agregado a tus favoritos!")

# Para agregar botón de "No me gusta":
def on_dislike_song(self):
    """Cuando el usuario no le gusta una canción"""
    self.update_user_preferences('dislike')
    # Opcional: saltar a la siguiente canción
    self.on_next()
