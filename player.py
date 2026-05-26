from kivy.logger import Logger
from kivy.utils import platform
from kivy.core.audio import SoundLoader
import os

# 1. Configuración de SDL (Inyección temprana)
if platform == "android":
    try:
        # Forzar driver OpenSL para menor latencia y estabilidad en Android - Crucial para Android 14
        os.environ['SDL_AUDIODRIVER'] = 'opensl'
        Logger.info("Player: Audio driver forzado a OpenSL")
    except Exception as e:
        # Fallback if Logger is not ready
        print(f"Player: No se pudo forzar OpenSL: {e}")

# Motores Opcionales
try:
    from ffpyplayer.player import MediaPlayer as FFMediaPlayer
    FFPY_AVAILABLE = True
except:
    FFPY_AVAILABLE = False

try:
    import vlc
    VLC_AVAILABLE = True
except:
    VLC_AVAILABLE = False

class AudioPlayerBase:
    """Senior Interface: Ensures all players are cross-compatible"""
    def play(self, mrl): raise NotImplementedError
    def pause(self): raise NotImplementedError
    def stop(self): raise NotImplementedError
    def is_playing(self) -> bool: return False
    def get_time(self) -> int: return 0
    def get_length(self) -> int: return 0
    def set_time(self, ms: int): pass
    def set_volume(self, volume: float): pass

def get_best_player():
    """Factory Pattern: Automatically selects the most stable engine"""
    if platform == 'android':
        try:
            return AndroidPlayer()
        except Exception as e:
            Logger.warning(f"Player: High-level AndroidPlayer failed: {e}")
            return KivyPlayer() # Fallback to Kivy SoundLoader
    
    # Desktop (Linux): Prefer VLC then FFmpeg for stable streaming & memory safety
    if VLC_AVAILABLE:
        try:
            Logger.info("Player: Seleccionando VLCPlayer (Recomendado para Linux)")
            return VLCPlayer()
        except Exception as e:
            Logger.debug(f"Player: VLC initialization failed: {e}")
    
    if FFPY_AVAILABLE:
        try:
            Logger.info("Player: Seleccionando FFPlayer (Fallback estable)")
            return FFPlayer()
        except Exception as e:
            Logger.debug(f"Player: FFmpeg initialization failed: {e}")
            
    Logger.info("Player: Seleccionando KivyPlayer (Último recurso, puede ser inestable en streams)")
    return KivyPlayer()

if platform == 'android':
    from jnius import PythonJavaClass, java_method # type: ignore
    class AndroidPreparedListener(PythonJavaClass):
        __javainterfaces__ = ['android/media/MediaPlayer$OnPreparedListener']
        __javacontext__ = 'app'
        def __init__(self, callback):
            super().__init__()
            self.callback = callback
        @java_method('(Landroid/media/MediaPlayer;)V')
        def onPrepared(self, mp):
            self.callback()

    class AudioFocusChangeListener(PythonJavaClass):
        __javainterfaces__ = ['android/media/AudioManager$OnAudioFocusChangeListener']
        __javacontext__ = 'app'
        def __init__(self, player):
            super().__init__()
            self.player = player
        @java_method('(I)V')
        def onAudioFocusChange(self, focusChange):
            # focusChange constants: Loss=-1, LossTransient=-2, Gain=1
            if focusChange <= 0: # Loss of focus (call, another app)
                self.player.on_focus_lost()

    class AndroidErrorListener(PythonJavaClass):
        """Atrapa bloqueos silenciosos de buffer o red en Android 14"""
        __javainterfaces__ = ['android/media/MediaPlayer$OnErrorListener']
        __javacontext__ = 'app'

        def __init__(self, callback):
            super().__init__()
            self.callback = callback

        @java_method('(Landroid/media/MediaPlayer;II)Z')
        def onError(self, mp, what, extra):
            self.callback(what, extra)
            return True # Event handled

class AndroidPlayer(AudioPlayerBase):
    """Motor 100% Nativo via Pyjnius (El estándar de oro para Android)"""
    def __init__(self):
        from jnius import autoclass  # type: ignore
        self.MediaPlayer = autoclass('android.media.MediaPlayer')
        self.AudioManager = autoclass('android.media.AudioManager')
        self.Context = autoclass('android.content.Context')
        self.activity = None 
        self.player = None
        self._is_playing = False
        self._temp_listener = None
        self._focus_listener = None
        self._err_listener = None
        self._prep_listener = None

    def play(self, mrl):
        try:
            self.stop() 
            
            from jnius import autoclass
            if not self.activity:
                self.activity = autoclass('org.kivy.android.PythonActivity').mActivity

            from android.runnable import run_on_ui_thread # type: ignore
            
            @run_on_ui_thread
            def _native_play_setup():
                try:
                    # Request Audio Focus BEFORE playing natively
                    self._request_focus()

                    self.player = self.MediaPlayer()
                    self.player.setAudioStreamType(self.AudioManager.STREAM_MUSIC)
                    
                    try:
                        Uri = autoclass('android.net.Uri')
                        uri = Uri.parse(mrl)
                        headers = autoclass('java.util.HashMap')()
                        headers.put("User-Agent", "Mozilla/5.0 (Android 14; Mobile; rv:115.0) Gecko/115.0 Firefox/115.0")
                        self.player.setDataSource(self.activity, uri, headers)
                    except Exception as ue:
                        self.player.setDataSource(mrl)

                    listener = AndroidPreparedListener(self._on_prepared)
                    self.player.setOnPreparedListener(listener)
                    self._temp_listener = listener 
                    
                    err_listener = AndroidErrorListener(self._on_error)
                    self.player.setOnErrorListener(err_listener)
                    self._err_listener = err_listener # Evitar recolección de basura
                    
                    self.player.prepareAsync()
                    self._is_playing = False
                except Exception as inner_e:
                    Logger.error(f"AndroidPlayer: Error nativo UI en play: {inner_e}")
            
            # Execute safely on Android Main Thread
            _native_play_setup()

        except Exception as e:
            Logger.error(f"AndroidPlayer: Excepción nativa JNI: {e}")
            raise

    def _on_error(self, what, extra):
        """Manejador de caída de red u otros estados corruptos de JNI"""
        try:
            from kivy.logger import Logger
            Logger.warning(f"AndroidPlayer: Native MediaPlayer Error Caught - what={what}, extra={extra}")
            
            # Filtramos errores inofensivos:
            # -38 = Illegal State Exception (Ocurre durante un seekTo asincrónico agresivo, es inofensivo)
            if extra == -38:
                return
            
            # -1004 = MEDIA_ERROR_IO (Caída pesada de red o URL de YouTube expirada)
            # -110 = MEDIA_ERROR_TIMED_OUT (Sin conexión)
            if extra in (-1004, -110) or what == 100:
                self._is_playing = False
                from kivy.app import App
                from kivy.clock import Clock
                app = App.get_running_app()
                Clock.schedule_once(lambda dt: app._on_playback_error(f"Red inestable ({what}/{extra})"), 0)
        except Exception: pass

    def _request_focus(self):
        """Manage Audio Focus to handle calls and system sounds"""
        try:
            # THIS MUST RUN ON UI THREAD AS IT USES activity.getSystemService
            am = self.activity.getSystemService(self.Context.AUDIO_SERVICE)
            if not self._focus_listener:
                self._focus_listener = AudioFocusChangeListener(self)
            
            # Request focus for music playback
            res = am.requestAudioFocus(self._focus_listener, self.AudioManager.STREAM_MUSIC, self.AudioManager.AUDIOFOCUS_GAIN)
            if res != 1: # 1 = AUDIOFOCUS_REQUEST_GRANTED
                Logger.warning("AndroidPlayer: Audio Focus denied")
        except Exception as e:
            Logger.warning(f"AndroidPlayer: Failed to request focus: {e}")

    def on_focus_lost(self):
        """Callback when focus is lost (system call, another app music, etc)"""
        if self._is_playing:
            Logger.info("AndroidPlayer: Focus lost, pausing...")
            self.pause()

    def _on_prepared(self):
        """Callback cuando el stream está listo"""
        try:
            if self.player:
                self.player.start()
                self.player.setVolume(1.0, 1.0)
                self._is_playing = True
                Logger.info("AndroidPlayer: ✓ Stream listo y reproduciendo")
        except Exception as e:
            Logger.error(f"AndroidPlayer: Error en onPrepared: {e}")

    def pause(self):
        if self.player:
            from android.runnable import run_on_ui_thread # type: ignore
            @run_on_ui_thread
            def _native_pause():
                try:
                    if self.player.isPlaying():
                        self.player.pause()
                        self._is_playing = False
                except Exception as e:
                    from kivy.logger import Logger
                    Logger.error(f"AndroidPlayer: Pause failed: {e}")
            _native_pause()

    def resume(self):
        if self.player:
            from android.runnable import run_on_ui_thread # type: ignore
            @run_on_ui_thread
            def _native_resume():
                try:
                    if not self.player.isPlaying():
                        self.player.start()
                        self._is_playing = True
                except Exception as e:
                    from kivy.logger import Logger
                    Logger.error(f"AndroidPlayer: Resume failed: {e}")
            _native_resume()

    def stop(self):
        if self.player:
            from android.runnable import run_on_ui_thread # type: ignore
            
            @run_on_ui_thread
            def _native_stop():
                try:
                    if self.player.isPlaying():
                        self.player.stop()
                    self.player.reset() 
                    self.player.release() 
                except Exception as e:
                    from kivy.logger import Logger
                    Logger.error(f"AndroidPlayer: Stop release failed: {e}")
                self.player = None
                self._is_playing = False
                
            _native_stop()
        
        # Release Listeners to avoid memory leaks
        self._temp_listener = None
        # Note: We keep _focus_listener to reuse it

    def is_playing(self) -> bool:
        if self.player:
            try: return bool(self.player.isPlaying())
            except: return False
        return False

    def get_time(self) -> int:
        if self.player:
            try: return self.player.getCurrentPosition()
            except: return 0
        return 0

    def get_length(self) -> int:
        if self.player:
            try: return self.player.getDuration()
            except: return 0
        return 0

    def set_volume(self, volume: float):
        if self.player:
            v = volume / 100.0
            try: self.player.setVolume(v, v)
            except: pass

    def set_time(self, time_ms: int):
        if self.player:
            from android.runnable import run_on_ui_thread # type: ignore
            @run_on_ui_thread
            def _native_seek():
                if not self.player:
                    return
                try:
                    # Optimization for Android 8.0+ (API 26)
                    from android import api_version # type: ignore
                    if api_version >= 26:
                        # SEEK_CLOSEST = 3
                        self.player.seekTo(int(time_ms), 3)
                    else:
                        self.player.seekTo(int(time_ms))
                        
                    # No forzamos .start() aquí porque Android 14 crashea (Error 38)
                    # si llamas a start() durante una operación de AsyncSeeking(). 
                    # El MediaPlayer de NuPlayer auto-reanuda solo si estaba sonando.
                except Exception as e:
                    Logger.error(f"AndroidPlayer: Seek error: {e}")
                    try: 
                        if self.player:
                            self.player.seekTo(int(time_ms)) # Fallback
                    except Exception as fe:
                        Logger.error(f"AndroidPlayer: Seek fallback failed: {fe}")
            _native_seek()

class KivyPlayer(AudioPlayerBase):
    """Motor Kivy SoundLoader (Fallback seguro)"""
    def __init__(self):
        self.player = None
        self._is_playing = False

    def play(self, mrl):
        try:
            self.stop()
            Logger.info(f"KivyPlayer: Loading {mrl[:50]}")
            
            self.player = SoundLoader.load(mrl)
            if self.player:
                self.player.play()
                self._is_playing = True
                Logger.info("KivyPlayer: ✓ Playback started")
            else:
                Logger.error("KivyPlayer: SoundLoader returned None")
                self._is_playing = False
                raise Exception("SoundLoader no pudo cargar el archivo")
        except Exception as e:
            Logger.error(f"KivyPlayer: Play error: {e}")
            self._is_playing = False

    def pause(self):
        if self.player and self.player.state == 'play':
            self.player.stop()
            self._is_playing = False

    def resume(self):
        if self.player and self.player.state != 'play':
            self.player.play()
            self._is_playing = True

    def stop(self):
        if self.player:
            try:
                self.player.stop()
                self.player.unload()
            except Exception as e:
                Logger.warning(f"KivyPlayer: Stop error: {e}")
            finally:
                self.player = None
                self._is_playing = False

    def is_playing(self) -> bool: 
        return bool(self._is_playing)
    
    def get_time(self) -> int: 
        try:
            if self.player:
                pos = self.player.get_pos()
                if pos is not None and pos >= 0:
                    return int(pos * 1000)
        except:
            pass
        return 0
    
    def get_length(self) -> int: 
        try:
            if self.player:
                length = self.player.length
                if length and length > 0:
                    return int(length * 1000)
        except:
            pass
        return 0
    
    def set_volume(self, volume: float):
        try:
            if self.player:
                v = volume / 100.0
                if 0 <= v <= 1:
                    self.player.volume = v
        except Exception as e:
            Logger.warning(f"KivyPlayer: set_volume: {e}")
    
    def set_time(self, time_ms: int):
        try:
            if self.player:
                time_sec = time_ms / 1000.0
                self.player.seek(time_sec)
        except Exception as e:
            Logger.warning(f"KivyPlayer: seek: {e}")

class FFPlayer(AudioPlayerBase):
    """Motor FFmpeg (Desktop/Advanced) - Versión Robusta"""
    def __init__(self):
        self.player = None
        self._is_playing = False

    def play(self, mrl):
        try:
            # Stop previous player gracefully
            self.stop()
            
            Logger.debug(f"FFPlayer: Playing URL (length: {len(mrl)})")
            
            try:
                self.player = FFMediaPlayer(mrl)
                self._is_playing = True
                Logger.info("FFPlayer: ✓ Player initialised")
            except Exception as init_err:
                Logger.error(f"FFPlayer: Initialization failed: {init_err}")
                self._is_playing = False
                raise
        except Exception as e:
            Logger.error(f"FFPlayer: Critical play error: {str(e)[:100]}")
            self._is_playing = False
            raise

    def pause(self):
        if self.player:
            try:
                self.player.toggle_pause()
                self._is_playing = not self._is_playing
            except Exception as e:
                Logger.warning(f"FFPlayer: Pause error: {e}")

    def stop(self):
        """Stop player and release resources safely"""
        if self.player:
            try:
                # Try to close gracefully
                self.player.close_player()
                Logger.debug("FFPlayer: Player closed successfully")
            except Exception as e:
                Logger.warning(f"FFPlayer: Error closing player: {e}")
            finally:
                # Always set to None
                self.player = None
                self._is_playing = False

    def is_playing(self) -> bool: 
        try:
            return bool(self._is_playing and self.player is not None)
        except:
            return False
    
    def get_time(self) -> int: 
        try:
            if self.player:
                pts = self.player.get_pts()
                if pts is not None and pts >= 0:
                    return int(pts * 1000)
            return 0
        except:
            return 0
    
    def get_length(self) -> int:
        try:
            if self.player:
                meta = self.player.get_metadata()
                if meta and isinstance(meta, dict): 
                    duration = meta.get('duration')
                    if duration and isinstance(duration, (int, float)) and duration > 0:
                        return int(duration * 1000)
        except Exception as e:
            Logger.debug(f"FFPlayer: get_length: {e}")
        return 0
    
    def set_volume(self, volume: float):
        try:
            if self.player and 0 <= volume <= 1:
                self.player.set_volume(volume)
        except Exception as e:
            Logger.warning(f"FFPlayer: set_volume: {e}")
    
    def set_time(self, time_ms: int):
        try:
            if self.player and time_ms >= 0:
                time_sec = time_ms / 1000.0
                self.player.seek(time_sec, relative=False)
                # Add small delay to allow buffering after seek
                import time as time_module
                time_module.sleep(0.1)
        except Exception as e:
            Logger.warning(f"FFPlayer: seek: {e}")

class VLCPlayer(AudioPlayerBase):
    """Motor VLC (El más estable para Streaming en Desktop)"""
    def __init__(self):
        try:
            self.instance = vlc.Instance("--quiet", "--no-xlib", "--network-caching=3000")
            self.player = self.instance.media_player_new()
            self._current_mrl = None
        except Exception as e:
            Logger.error(f"VLCPlayer: Error al inicializar: {e}")
            raise

    def play(self, mrl):
        try:
            self.stop()
            self._current_mrl = mrl
            media = self.instance.media_new(mrl)
            self.player.set_media(media)
            self.player.play()
            Logger.info(f"VLCPlayer: Reproduciendo {mrl[:50]}")
        except Exception as e:
            Logger.error(f"VLCPlayer: Error en play: {e}")
            raise

    def pause(self):
        """VLC toggle_pause is safer than pause() for stream sources."""
        if self.player:
            self.player.pause()  # VLC: toggles play/pause

    def resume(self):
        """Resume without reloading the MRL. VLC .play() resumes if paused."""
        try:
            if self.player and not self.player.is_playing():
                self.player.play()  # In VLC, play() on a paused player resumes it
                Logger.info("VLCPlayer: Resumed after seek")
        except Exception as e:
            Logger.error(f"VLCPlayer: Resume error: {e}")

    def stop(self):
        if self.player:
            self.player.stop()

    def is_playing(self) -> bool:
        return bool(self.player and self.player.is_playing())

    def get_time(self) -> int:
        return int(self.player.get_time()) if self.player else 0

    def get_length(self) -> int:
        return int(self.player.get_length()) if self.player else 0

    def set_volume(self, volume: float):
        if self.player:
            self.player.audio_set_volume(int(volume))

    def set_time(self, time_ms: int):
        """Seek without stopping the media — VLC handles this natively."""
        if self.player:
            self.player.set_time(int(time_ms))
