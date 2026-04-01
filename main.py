import os
import sys
import threading
import random
from concurrent.futures import ThreadPoolExecutor
from kivy.utils import platform
from kivy.config import Config

# Enforce aggressive texture cache limits for memory stability
Config.set('kivy', 'image_cache_limit', '50')
Config.set('kivy', 'texture_cache_limit', '50')

if platform == "android":
    Config.set('graphics', 'max_fps', '60')
    Config.set('graphics', 'multisamples', '0')
    Config.set('kivy', 'exit_on_escape', '0')

import gc
import json

from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView

from kivy.logger import Logger
from kivymd.app import MDApp
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.uix.screenmanager import SlideTransition
from kivymd.uix.button import MDIconButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.list import (
    TwoLineAvatarIconListItem,
    OneLineAvatarListItem,
    OneLineAvatarIconListItem,
    OneLineListItem,
    ImageLeftWidget,
    IconLeftWidget,
    IconRightWidget,
    MDList,
    IRightBodyTouch
)
from kivy.uix.recycleview import RecycleView
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel
from kivymd.uix.slider import MDSlider
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.fitimage import FitImage
from kivymd.uix.dialog import MDDialog
from kivymd.toast import toast
from kivymd.uix.snackbar import MDSnackbar

from extractor import get_audio_url, search_youtube, get_recommendations, download_audio
from player import get_best_player

if platform == 'android':
    from jnius import autoclass, cast, java_method, PythonJavaClass # type: ignore
    from android import api_version, mActivity # type: ignore
    
    # Lazy JNI setup to avoid startup instability on Android 14
    String = None
    
    def setup_jni_globals():
        global String
        if String is None:
            String = autoclass('java.lang.String')

    class MediaActionReceiver(PythonJavaClass):
        __javacontext__ = 'app'
        __javabaseclass__ = 'android/content/BroadcastReceiver'
        __javainterfaces__ = []
        
        def __init__(self, app_instance):
            self.app = app_instance
            
        @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
        def onReceive(self, context, intent):
            try:
                action = intent.getAction()
                Logger.info(f"App: MediaActionReceiver onReceive: {action}")
                if action == "org.test.musicplayeryt.ACTION_PLAY":
                    if not self.app.player.is_playing(): self.app.toggle_playback()
                elif action == "org.test.musicplayeryt.ACTION_PAUSE":
                    if self.app.player.is_playing(): self.app.toggle_playback()
                elif action == "org.test.musicplayeryt.ACTION_NEXT":
                    self.app.on_next()
                elif action == "org.test.musicplayeryt.ACTION_PREV":
                    self.app.on_previous()
            except Exception as e:
                Logger.error(f"App: MediaActionReceiver Error: {e}")

    class MediaSessionCallback(PythonJavaClass):
        __javacontext__ = 'app'
        __javabaseclass__ = 'android/media/session/MediaSession$Callback'
        __javainterfaces__ = []
        
        def __init__(self, app_instance):
            self.app = app_instance
            
        @java_method('()V')
        def onPlay(self):
            Logger.info("App: MediaSessionCallback onPlay")
            if not self.app.player.is_playing(): self.app.toggle_playback()
        
        @java_method('()V')
        def onPause(self):
            Logger.info("App: MediaSessionCallback onPause")
            if self.app.player.is_playing(): self.app.toggle_playback()
        
        @java_method('()V')
        def onSkipToNext(self):
            Logger.info("App: MediaSessionCallback onSkipToNext")
            self.app.on_next()
        
        @java_method('()V')
        def onSkipToPrevious(self):
            Logger.info("App: MediaSessionCallback onSkipToPrevious")
            self.app.on_previous()
        
        @java_method('(J)V')
        def onSeekTo(self, pos):
            Logger.info(f"App: MediaSessionCallback onSeekTo: {pos}")
            duration = self.app.player.get_length()
            if duration > 0: self.app.seek_media((pos / duration) * 100)

# UI Classes for RecycleView
class SearchItem(TwoLineAvatarIconListItem):
    title = StringProperty()
    artist = StringProperty()
    index = NumericProperty()
    thumbnail = StringProperty()
    song_data = ObjectProperty()
    is_playlist_view = BooleanProperty(False)

# UI Classes for RecycleView

class PlaylistItem(OneLineAvatarIconListItem):
    text = StringProperty()
    playlist_name = StringProperty()

class OfflineItem(TwoLineAvatarIconListItem):
    title = StringProperty()
    artist = StringProperty()
    index = NumericProperty()
    song_data = ObjectProperty()

# UI Definition in KV Language
KV = '''
<SearchItem>:
    text: root.title
    secondary_text: root.artist
    theme_text_color: "Custom"
    text_color: "#BB86FC"
    on_release: app.play_selected_song(root.index)
    
    AsyncImage:
        source: root.thumbnail
        size_hint: None, None
        size: dp(40), dp(40)
        allow_stretch: True
        keep_ratio: True
    
    IconRightWidget:
        icon: "trash-can" if root.is_playlist_view else "playlist-plus"
        on_release: app.on_item_right_button(root)

<PlaylistItem>:
    text: root.text
    on_release: app.open_playlist(root.text)
    IconLeftWidget:
        icon: "playlist-music"
    IconRightWidget:
        icon: "trash-can"
        theme_text_color: "Custom"
        text_color: 1, 0, 0, 1
        on_release: app.delete_playlist(root.text)

<OfflineItem>:
    text: root.title
    secondary_text: root.artist
    theme_text_color: "Custom"
    text_color: "#BB86FC"
    on_release: app.play_local_song(root.index)
    IconLeftWidget:
        icon: "music-note"
        theme_text_color: "Custom"
        icon_color: "#BB86FC"
    IconRightWidget:
        icon: "trash-can"
        theme_text_color: "Custom"
        text_color: 1, 0, 0, 1
        on_release: app.delete_downloaded_song(root.song_data.get('url'))

MDScreenManager:
    ScreenLibrary:
    ScreenPlayer:
    ScreenOffline:
    ScreenPlaylists:

<ScreenLibrary>:
    name: "library"
    md_bg_color: "#000000"
    
    MDBoxLayout:
        orientation: "vertical"
        padding: [0, "56dp", 0, 0]
        
        MDTopAppBar:
            title: "Mi Biblioteca"
            anchor_title: "center"
            elevation: 0
            md_bg_color: "#000000"
            specific_text_color: "#BB86FC"
            right_action_items: [["playlist-music", lambda x: app.go_to_playlists()], ["folder-music", lambda x: app.go_to_offline()], ["magnify", lambda x: app.search_songs(search_input.text)]]

        MDBoxLayout:
            orientation: "vertical"
            padding: "20dp"
            spacing: "15dp"

            MDTextField:
                id: search_input
                hint_text: "Busca tu música favorita..."
                mode: "fill"
                fill_color_normal: "#000000"
                hint_text_color_normal: "#888888"
                text_color_normal: "#BB86FC"
                icon_left: "youtube"
                icon_left_color_normal: "#FF0000"
                active_line_color_normal: "#BB86FC"
                on_text_validate: app.search_songs(self.text)

            MDLabel:
                id: list_header
                text: "RECOMENDADOS PARA TI"
                theme_text_color: "Custom"
                text_color: "#BB86FC"
                font_style: "Overline"
                adaptive_height: True
            
            RecycleView:
                id: results_rv
                viewclass: 'SearchItem'
                RecycleBoxLayout:
                    default_size: None, dp(72)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(10)

            MDSpinner:
                id: search_spinner
                size_hint: (None, None)
                size: (dp(40), dp(40))
                pos_hint: {'center_x': .5, 'center_y': .5}
                active: False
                color: "#BB86FC"

    MDFloatingActionButton:
        icon: "music-note"
        md_bg_color: "#BB86FC"
        pos_hint: {"center_x": .9, "center_y": .08}
        on_release: app.go_to_player()

<ScreenOffline>:
    name: "offline"
    md_bg_color: "#000000"
    
    MDBoxLayout:
        orientation: "vertical"
        padding: [0, "56dp", 0, 0]
        
        MDTopAppBar:
            title: "Música Descargada"
            elevation: 0
            md_bg_color: "#000000"
            specific_text_color: "#BB86FC"
            left_action_items: [["arrow-left", lambda x: app.go_to_library()]]
            right_action_items: [["folder-settings", lambda x: app.open_file_manager()]]

        RecycleView:
            id: offline_rv
            viewclass: 'OfflineItem'
            RecycleBoxLayout:
                default_size: None, dp(72)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                spacing: dp(10)

    MDFloatingActionButton:
        icon: "refresh"
        md_bg_color: "#BB86FC"
        pos_hint: {"center_x": .9, "center_y": .08}
        on_release: app.load_offline_songs()

<ScreenPlaylists>:
    name: "playlists"
    md_bg_color: "#000000"
    
    MDBoxLayout:
        orientation: "vertical"
        padding: [0, "56dp", 0, 0]
        
        MDTopAppBar:
            title: "Mis Playlists"
            elevation: 0
            md_bg_color: "#000000"
            specific_text_color: "#BB86FC"
            left_action_items: [["arrow-left", lambda x: app.go_to_library()]]
            right_action_items: [["plus", lambda x: app.create_playlist_dialog()]]

        RecycleView:
            id: playlists_rv
            viewclass: 'PlaylistItem'
            RecycleBoxLayout:
                default_size: None, dp(56)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                spacing: dp(10)

<ScreenPlayer>:
    name: "player"
    md_bg_color: "#000000"
    
    MDBoxLayout:
        orientation: "vertical"
        padding: [0, "56dp", 0, "20dp"]
        spacing: "10dp"
        
        MDTopAppBar:
            title: ""
            elevation: 0
            md_bg_color: "#000000"
            left_action_items: [["chevron-down", lambda x: app.go_to_library()]]
            right_action_items: [["playlist-plus", lambda x: app.add_song_to_playlist_dialog(app.get_current_song_data())], ["download", lambda x: app.download_song()]]
            specific_text_color: "#BB86FC"

        # Central Rounded Art
        MDBoxLayout:
            orientation: "vertical"
            size_hint_y: 0.45
            padding: ["40dp", "10dp"]
            
            MDCard:
                id: album_card
                size_hint: (1, 1)
                radius: [30,]
                elevation: 0
                md_bg_color: "#000000"
                canvas.before:
                    PushMatrix
                    Scale:
                        origin: self.center
                        x: app.album_scale
                        y: app.album_scale
                canvas.after:
                    PopMatrix
                
                FitImage:
                    id: thumbnail
                    source: ""
                    radius: [30,]
            
            MDSpinner:
                id: loading_spinner
                size_hint: (None, None)
                size: (dp(46), dp(46))
                pos_hint: {'center_x': .5, 'center_y': .5}
                active: False
                color: "#BB86FC"

        # Song Information
        MDBoxLayout:
            orientation: "vertical"
            adaptive_height: True
            spacing: "5dp"
            padding: ["24dp", "10dp"]
            
            MDLabel:
                id: song_title
                text: "Título de la canción"
                halign: "center"
                theme_text_color: "Custom"
                text_color: [0.73, 0.52, 0.98, app.title_glow] # Purple Neon Glow
                font_style: "H6"
                bold: True
                adaptive_height: True
            
            MDLabel:
                id: artist_name
                text: "Artista"
                halign: "center"
                theme_text_color: "Custom"
                text_color: "#AAAAAA"
                font_style: "Subtitle2"
                adaptive_height: True

        Widget:
            size_hint_y: 0.1

        # Ergonomic Control Section
        MDBoxLayout:
            orientation: "vertical"
            adaptive_height: True
            spacing: "15dp"
            padding: ["24dp", "10dp"]
            
            # Subtle Progress Slider with Seek Buttons
            MDBoxLayout:
                orientation: "horizontal"
                adaptive_size: True
                pos_hint: {"center_x": .5}
                spacing: "10dp"
                
                MDIconButton:
                    icon: "rewind-10"
                    user_font_size: "24sp"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.seek_relative(-10)
                
                MDSlider:
                    id: progress_slider
                    size_hint: (None, None)
                    width: dp(240)
                    height: dp(40)
                    min: 0
                    max: 100
                    value: 0
                    color: "#BB86FC"
                    hint: False

                MDIconButton:
                    icon: "fast-forward-10"
                    user_font_size: "24sp"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.seek_relative(10)

            MDBoxLayout:
                orientation: "horizontal"
                adaptive_size: True
                pos_hint: {"center_x": .5}
                spacing: "180dp"  # Space between current and total time
                MDLabel:
                    id: current_time_label
                    text: "00:00"
                    font_size: "12sp"
                    theme_text_color: "Custom"
                    text_color: "#888888"
                    size_hint: (None, None)
                    size: (dp(40), dp(20))
                MDLabel:
                    id: total_time_label
                    text: "00:00"
                    font_size: "12sp"
                    theme_text_color: "Custom"
                    text_color: "#888888"
                    halign: "right"
                    size_hint: (None, None)
                    size: (dp(40), dp(20))

            # Extra Controls (Shuffle, Repeat, Download)
            MDBoxLayout:
                orientation: "horizontal"
                adaptive_size: True
                pos_hint: {"center_x": .5}
                spacing: "50dp"
                MDIconButton:
                    id: shuffle_btn
                    icon: "shuffle"
                    user_font_size: "24sp"
                    theme_text_color: "Custom"
                    text_color: "#444444"
                    on_release: app.toggle_shuffle()
                MDIconButton:
                    id: repeat_btn
                    icon: "repeat"
                    user_font_size: "24sp"
                    theme_text_color: "Custom"
                    text_color: "#444444"
                    on_release: app.toggle_repeat()
                MDIconButton:
                    id: download_btn
                    icon: "download"
                    user_font_size: "24sp"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.download_song()

            # Main Controls (Large & Perfectly Centered)
            MDBoxLayout:
                orientation: "horizontal"
                adaptive_size: True
                pos_hint: {"center_x": .5}
                spacing: "40dp"

                MDIconButton:
                    icon: "skip-previous"
                    user_font_size: "64sp"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.on_previous()
                
                MDIconButton:
                    id: play_pause_btn
                    icon: "pause-circle"
                    user_font_size: "100sp"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.toggle_playback()

                MDIconButton:
                    icon: "skip-next"
                    user_font_size: "64sp"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.on_next()

'''

class ScreenLibrary(MDScreen):
    pass

class ScreenOffline(MDScreen):
    pass

class ScreenPlaylists(MDScreen):
    pass

class ScreenPlayer(MDScreen):
    pass

class MusicPlayerApp(MDApp):
    is_shuffle = BooleanProperty(False)
    is_repeat = BooleanProperty(False)
    is_seeking = BooleanProperty(False)
    album_scale = NumericProperty(1.0)
    title_glow = NumericProperty(1.0)
    # Track what is currently being shown on the library screen
    # Modes: 'recommendations', 'search', 'playlist', 'offline'
    library_mode = StringProperty('recommendations')

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
        self.current_playlist_name = ""  # Track which playlist is being viewed
        self.last_results = []
        self.recommendations_cache = []  # Store initial results to go back fast
        self.search_history = []
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

    def _init_music_path(self):
        """Set up the default music storage directory with API 34 awareness"""
        if platform == "android":
            try:
                from android.storage import primary_external_storage_path # type: ignore
                storage_path = primary_external_storage_path()
                # Check for MANAGE_EXTERNAL_STORAGE for API 30+
                self.music_path = os.path.join(storage_path, "Download", "ReproductorGolomn")
            except Exception as e:
                Logger.warning(f"App: Could not get primary storage: {e}")
                self.music_path = "/sdcard/Download/ReproductorGolomn"
        else:
            self.music_path = os.path.join(os.path.expanduser("~"), "Downloads", "ReproductorGolomn")
        
        try:
            # Recursive creation for safety
            if not os.path.exists(self.music_path):
                os.makedirs(self.music_path, exist_ok=True)
                Logger.info(f"App: Folder created at {self.music_path}")
        except Exception as e:
            Logger.debug(f"App: Initial folder creation failed (Permission?): {e}")

    def _init_animations(self):
        """Create standard animations used across the app"""
        self.pulse_anim = Animation(album_scale=1.03, title_glow=0.6, duration=1, t='in_out_quad') + \
                         Animation(album_scale=1.0, title_glow=1.0, duration=1, t='in_out_quad')
        self.pulse_anim.repeat = True
        
    def _load_playlists_async(self):
        """Thread-safe playlist loader. Path MUST be user_data_dir for Android compatibility."""
        try:
            # On Android, ONLY user_data_dir is a safe read/write path (no permission needed)
            app = MDApp.get_running_app()
            safe_path = os.path.join(app.user_data_dir, 'playlists.json')
            Logger.info(f"App: Loading playlists from {safe_path}")
            if os.path.exists(safe_path):
                with open(safe_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # UI update MUST be via Clock.schedule_once from non-main thread
                    Clock.schedule_once(lambda dt, d=data: self._update_playlists_state(d))
        except Exception as e:
            Logger.warning(f"App: Failed to load playlists: {e}")

    @mainthread
    def _update_playlists_state(self, data):
        self.playlists = data
        Logger.info("App: Playlists loaded successfully")

    def save_playlists_data(self):
        """Persistent playlist storage saver (Threaded to avoid ANR)"""
        threading.Thread(target=self._do_save_playlists, daemon=True).start()

    def _do_save_playlists(self):
        try:
            # ONLY user_data_dir is guaranteed writable without permissions on Android
            app = MDApp.get_running_app()
            save_dir = app.user_data_dir
            os.makedirs(save_dir, exist_ok=True)
            path = os.path.join(save_dir, 'playlists.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=4)
            Logger.info(f"App: Playlists saved to {path}")
        except Exception as e:
            Logger.error(f"App: Failed to save playlists: {e}")
            Clock.schedule_once(lambda dt: toast("Error al guardar"))

    def go_to_playlists(self):
        self.root.transition = SlideTransition(direction="left")
        self.root.current = "playlists"
        self.display_playlists()

    def go_to_offline(self):
        self.root.transition = SlideTransition(direction="right")
        self.root.current = "offline"
        self.load_offline_songs()

    def build(self):
        if platform != "android":
            Window.size = (400, 880)
            
        self.theme_cls.primary_palette = "DeepPurple"
        self.theme_cls.theme_style = "Dark"
        # AMOLED: Use Window.clearcolor directly
        Window.clearcolor = (0, 0, 0, 1)
        
        if platform == "android":
            try:
                from android.runnable import run_on_ui_thread  # type: ignore
                @run_on_ui_thread
                def set_status_bar_color():
                    try:
                        from jnius import autoclass  # type: ignore
                        WindowManager = autoclass('android.view.WindowManager$LayoutParams')
                        Color = autoclass('android.graphics.Color')
                        activity = autoclass('org.kivy.android.PythonActivity').mActivity
                        window = activity.getWindow()
                        window.addFlags(WindowManager.FLAG_DRAWS_SYSTEM_BAR_BACKGROUNDS)
                        # Use parsed colors instead of Python integer to prevent JNI OverflowError
                        window.setStatusBarColor(Color.parseColor("#000000"))
                        window.setNavigationBarColor(Color.parseColor("#000000"))
                    except Exception as inner_e:
                        Logger.warning(f"App: Could not color navbar: {inner_e}")
                set_status_bar_color()
            except: pass

        root = Builder.load_string(KV)
        
        # Bind Slider & Back Button
        slider = root.get_screen("player").ids.progress_slider
        slider.bind(on_touch_down=self._slider_touch_down)
        slider.bind(on_touch_up=self._slider_touch_up)
        
        # Back button event & window focus events
        Window.bind(on_keyboard=self.on_key)
        if platform != "android":
            # Desktop: handle window minimize/restore
            Window.bind(on_minimize=self._on_window_minimize)
            Window.bind(on_restore=self._on_window_restore)
        
        return root

    def on_key(self, window, key, *args):
        """Back button handler: navigate screens or ask to exit."""
        if key == 27:  # Android back / Desktop Escape
            # Priority 1: Close the file manager if open
            if hasattr(self, 'manager_open') and self.manager_open:
                self.exit_manager()
                return True
            
            # Priority 2: Close any open dialog
            for attr in ('playlist_dialog', 'add_dialog'):
                dlg = getattr(self, attr, None)
                if dlg:
                    try:
                        dlg.dismiss()
                        setattr(self, attr, None)
                        return True
                    except: pass
            
            # Priority 3: Navigate back through screens
            current = self.root.current
            screen_back_map = {
                'player':    'library',
                'playlists': 'library',
                'offline':   'library',
            }
            if current in screen_back_map:
                self.root.transition = SlideTransition(direction='right')
                self.root.current = screen_back_map[current]
                return True
            
            # Priority 4: On the main screen — handle playlist view / search or exit
            if current == 'library':
                # 1. Check if we are viewing a playlist or search results
                if self.library_mode != 'recommendations':
                    self.library_mode = 'recommendations'
                    # Restore cached recommendations instantly if they exist
                    if self.recommendations_cache:
                        self._update_results_rv(self.recommendations_cache, "RECOMENDADOS PARA TI")
                    else:
                        # Fallback: re-fetch if cache is empty
                        threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
                    
                    # Also clear search input for clean UI
                    try:
                        self.root.get_screen("library").ids.search_input.text = ""
                    except: pass
                    return True
                
                # 2. If already in recommendations, show exit dialog
                self._show_exit_dialog()
                return True
        
        return False

    def _show_exit_dialog(self):
        """Show a confirmation dialog before exiting the app."""
        try:
            from kivymd.uix.dialog import MDDialog
            from kivymd.uix.button import MDFlatButton
            if hasattr(self, '_exit_dialog') and self._exit_dialog:
                self._exit_dialog.open()
                return
            self._exit_dialog = MDDialog(
                title="¿Salir de la app?",
                text="¿Deseas cerrar el reproductor?",
                buttons=[
                    MDFlatButton(
                        text="CANCELAR",
                        on_release=lambda x: self._exit_dialog.dismiss()
                    ),
                    MDFlatButton(
                        text="SALIR",
                        theme_text_color="Custom",
                        text_color="#BB86FC",
                        on_release=lambda x: self.stop()
                    ),
                ]
            )
            self._exit_dialog.open()
        except Exception as e:
            Logger.error(f"App: Exit dialog error: {e}")
            self.stop()

    def _on_window_minimize(self, window):
        """Handle window minimize event (pause UI updates only)"""
        Logger.info("App: Ventana minimizada (UI updates suspended)")
        try:
            if self.update_event:
                self.update_event.cancel()
                self.update_event = None
        except Exception as e:
            Logger.warning(f"App: Error minimizing: {e}")

    def _on_window_restore(self, window):
        """Handle window restore event (resume UI updates)"""
        Logger.info("App: Ventana restaurada (UI updates resumed)")
        try:
            # Safety: always cancel old event first
            if self.update_event:
                self.update_event.cancel()
                self.update_event = None
            
            # Restart update loop only if player is active
            if self.player and self.player.is_playing():
                self.update_event = Clock.schedule_interval(self._update_ui, 0.5)
        except Exception as e:
            Logger.warning(f"App: Error restoring: {e}")

    def _slider_touch_down(self, instance, touch):
        if instance.collide_point(*touch.pos):
            self.is_seeking = True

    def _slider_touch_up(self, instance, touch):
        if self.is_seeking:
            self.is_seeking = False
            self.seek_media(instance.value)

    def _cancel_update_event(self):
        """Helper to safely cancel the UI sync clock"""
        if self.update_event:
            self.update_event.cancel()
            self.update_event = None

    def on_stop(self):
        """Purge memory and release resources on exit"""
        try:
            self._cancel_update_event()
            if self.player:
                self.player.stop()
            
            # Aggressive cache clearing for Android stability
            from kivy.cache import Cache
            Cache.remove('kv.image')
            Cache.remove('kv.texture')
            
            # Explicit garbage collection
            gc.collect()
            Logger.info("App: Memory purged and resources released")
        except Exception as e:
            Logger.warning(f"App: Error in on_stop: {e}")

    def on_pause(self):
        """Suspend UI updates but keep audio playing in background"""
        self._cancel_update_event()
        Logger.info("App: Paused (UI suspended, audio continues)")
        return True # CRUCIAL: Must be True to keep Kivy alive in background on Android

    def on_resume(self):
        """Resume UI updates when returning to foreground"""
        Logger.info("App: Resumed (UI sync restored)")
        if self.player and self.player.is_playing():
            self._cancel_update_event()
            self.update_event = Clock.schedule_interval(self._update_ui, 0.5)

    def on_start(self):
        """Initialization after app is fully built"""
        Logger.info("App: Starting initialization...")
        
        # 1. Initialize Paths & Storage
        self._init_music_path()
        
        # 2. Initialize player here to ensure Android Activity is ready
        if not self.player:
            try:
                from player import get_best_player
                self.player = get_best_player()
                Logger.info("App: Audio engine initialized successfully")
            except Exception as e:
                Logger.error(f"App: Failed to initialize player: {e}")
                self.player = None

        # 3. Android setup - simplified and delayed
        if platform == "android":
            Logger.info("App: Scheduling Android setup...")
            Clock.schedule_once(lambda dt: self._deferred_android_setup(), 3.0)
        
        # 4. Load recommendations in background thread (with error handling)
        try:
            threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
        except Exception as e:
            Logger.error(f"App: Failed to start recommendations thread: {e}")

    def _deferred_android_setup(self):
        """Simplified Android setup with error handling"""
        try:
            Logger.info("App: Starting Android setup...")
            setup_jni_globals()
            Logger.info("App: JNI globals setup complete")
            
            # Simplified permissions - only essential ones
            self._request_android_permissions()
            Logger.info("App: Android setup complete")
        except Exception as e:
            Logger.error(f"App: Android setup failed: {e}")
            # Continue without Android-specific features
        
        # 4. Load recommendations in background thread
        threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()

    def _request_android_permissions(self):
        """Simplified permission request"""
        try:
            from android.permissions import request_permissions, Permission # type: ignore
            
            # Only request essential permissions
            perms = [Permission.INTERNET, Permission.WAKE_LOCK]
            
            Logger.info(f"App: Requesting essential permissions: {perms}")
            request_permissions(perms, self._on_permissions_callback)
        except Exception as e:
            Logger.error(f"App: Permissions error: {e}")
            # Continue without permissions

    def _on_permissions_callback(self, permissions, grants):
        """Callback for permission result"""
        for p, g in zip(permissions, grants):
            if not g:
                Logger.warning(f"App: Permission {p} denied")
        
        # Start playback service AFTER permissions have been requested/granted
        try:
            self._start_playback_service()
        except Exception as e:
            Logger.error(f"App: Failed to start playback service: {e}")
            # Continue without service

    def _check_manage_storage_permission(self):
        """Navigate user to 'All Files Access' settings if necessary"""
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread # type: ignore
            
            @run_on_ui_thread
            def _ask_storage_ui():
                try:
                    Environment = autoclass('android.os.Environment')
                    if not Environment.isExternalStorageManager():
                        toast("CONCEDE ACCESO A TODOS LOS ARCHIVOS PARA DESCARGAS")
                        Intent = autoclass('android.content.Intent')
                        Settings = autoclass('android.provider.Settings')
                        Uri = autoclass('android.net.Uri')
                        intent = Intent(Settings.ACTION_MANAGE_APP_ALL_FILES_ACCESS_PERMISSION)
                        PythonActivity = autoclass('org.kivy.android.PythonActivity')
                        uri = Uri.fromParts("package", PythonActivity.mActivity.getPackageName(), None)
                        intent.setData(uri)
                        PythonActivity.mActivity.startActivity(intent)
                except Exception as inner_e:
                    Logger.warning(f"App: Could not request MANAGE_EXTERNAL_STORAGE: {inner_e}")
            
            _ask_storage_ui()
        except Exception as e:
            Logger.warning(f"App: Error initializing storage request: {e}")

    def _start_playback_service(self):
        """Start the background service using p4a's AndroidService API (correct method)."""
        if platform == "android": setup_jni_globals()
        try:
            from android.runnable import run_on_ui_thread  # type: ignore
            from jnius import autoclass  # type: ignore

            @run_on_ui_thread
            def _do_start():
                try:
                    # METHOD 1: Use p4a's AndroidService bridge (THE correct way)
                    # This is what python-for-android generates and expects to be called.
                    PythonService = autoclass('org.kivy.android.PythonService')
                    mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
                    
                    Context = autoclass('android.content.Context')
                    Intent = autoclass('android.content.Intent')
                    
                    # The service class name that buildozer generates from services = playback:service.py
                    service_name = 'org.test.musicplayeryt.ServicePlayback'
                    
                    intent = Intent()
                    # FIX (JNI): Use (String, String) signature to avoid Context/String ambiguity
                    intent.setClassName(mActivity.getPackageName(), service_name)
                    intent.putExtra('androidPrivate', mActivity.getFilesDir().getAbsolutePath())
                    intent.putExtra('androidArgument', '')
                    intent.putExtra('serviceEntrypoint', 'service.py')
                    intent.putExtra('pythonName', 'playback')
                    intent.putExtra('pythonHome', mActivity.getFilesDir().getAbsolutePath())
                    intent.putExtra('pythonPath', mActivity.getFilesDir().getAbsolutePath())
                    intent.putExtra('backgroundService', True)
                    
                    # Use startForegroundService for Android 8+ to avoid background restrictions
                    from android import api_version  # type: ignore
                    if api_version >= 26:
                        mActivity.startForegroundService(intent)
                        Logger.info("App: startForegroundService called successfully")
                    else:
                        mActivity.startService(intent)
                        Logger.info("App: startService called successfully")
                    Logger.info(f"App: ServicePlayback attempt done — service_name={service_name}")
                except Exception as e:
                    Logger.error(f"App: Service start failed, building fallback notification: {e}")
                    # METHOD 2: Build the notification directly from the Activity as a fallback
                    # This ensures users ALWAYS see controls even if the service fails.
                    Clock.schedule_once(lambda dt: self._build_activity_notification(), 0.5)

            _do_start()
        except Exception as e:
            Logger.error(f"App: _start_playback_service error: {e}")

    def _build_activity_notification(self):
        """Fallback: build the MediaStyle notification directly from the Activity context."""
        if platform == "android": setup_jni_globals()
        try:
            from jnius import autoclass, PythonJavaClass, java_method # type: ignore
            from android import api_version  # type: ignore

            mActivity = autoclass('org.kivy.android.PythonActivity').mActivity
            Context = autoclass('android.content.Context')
            NotificationManager = autoclass('android.app.NotificationManager')
            NotificationChannel = autoclass('android.app.NotificationChannel')
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            NotificationAction = autoclass('android.app.Notification$Action$Builder')
            MediaSession = autoclass('android.media.session.MediaSession')
            MediaStyle = autoclass('android.app.Notification$MediaStyle')
            Intent = autoclass('android.content.Intent')
            PendingIntent = autoclass('android.app.PendingIntent')
            R_drawable = autoclass('android.R$drawable')

            channel_id = 'notif_audio_v4_fix'
            nm = mActivity.getSystemService(Context.NOTIFICATION_SERVICE)

            # FIX: resolve mipmap/icon resource ID (avoids missing-drawable crash)
            Resources = mActivity.getResources()
            pkg       = mActivity.getPackageName()
            _icon_res = Resources.getIdentifier('icon', 'mipmap', pkg)
            if _icon_res == 0:
                _icon_res = autoclass('android.R$drawable').ic_media_play

            if api_version >= 26:
                ch = NotificationChannel(channel_id, 'Música', NotificationManager.IMPORTANCE_MAX)
                ch.setLockscreenVisibility(1)  # VISIBILITY_PUBLIC
                nm.createNotificationChannel(ch)

            FLAG_UPDATE_CURRENT = 0x08000000
            FLAG_IMMUTABLE = 0x04000000
            pi_flags = FLAG_UPDATE_CURRENT | FLAG_IMMUTABLE

            pkg = mActivity.getPackageName()
            def make_pi(action, code):
                i = Intent(action)
                i.setPackage(pkg)  # CRITICAL for Android 14
                return PendingIntent.getBroadcast(mActivity, code, i, pi_flags)

            pi_play  = make_pi("org.test.musicplayeryt.ACTION_PLAY",  10)
            pi_pause = make_pi("org.test.musicplayeryt.ACTION_PAUSE", 11)
            pi_next  = make_pi("org.test.musicplayeryt.ACTION_NEXT",  12)
            pi_prev  = make_pi("org.test.musicplayeryt.ACTION_PREV",  13)

            # Store globally to update later
            self._notif_pi = {'play': pi_play, 'pause': pi_pause, 'next': pi_next, 'prev': pi_prev}
            self._notif_nm = nm
            self._notif_channel = channel_id
            self._notif_activity = mActivity

            # Build MediaSession
            ms = MediaSession(mActivity, String('KivyActivitySession'))
            self._media_session_act = ms  # Keep global reference
            
            # Set Flags: FLAG_HANDLES_MEDIA_BUTTONS (1) | FLAG_HANDLES_TRANSPORT_CONTROLS (2) = 3
            ms.setFlags(3)
            # Set null MediaButtonReceiver to force use of setCallback
            ms.setMediaButtonReceiver(None)
            
            # Use module-level classes
            self._session_callback = MediaSessionCallback(self)
            ms.setCallback(self._session_callback)

            # FIX: Set PlaybackState (MANDATORY for Android 13+ lockscreen)
            PlaybackStateBuilder = autoclass('android.media.session.PlaybackState$Builder')
            psb = PlaybackStateBuilder()
            # Actions: PLAY(4), PAUSE(2), NEXT(32), PREV(16), SEEK(256), PLAY_PAUSE(512) = 822
            psb.setActions(822) 
            psb.setState(3, 0, 1.0) # STATE_PLAYING = 3
            ms.setPlaybackState(psb.build())
            
            # Activate last!
            ms.setActive(True)

            style = MediaStyle()
            style.setMediaSession(ms.getSessionToken())
            style.setShowActionsInCompactView(0, 1, 2)

            b = NotificationBuilder(mActivity) 
            if api_version >= 26:
                b.setChannelId(channel_id)
            
            b.setContentTitle('Reproductor Activo')
            b.setContentText('Escuchando música...')
            b.setSmallIcon(_icon_res)  # FIX: mipmap resource
            b.addAction(NotificationAction(_icon_res, String('Prev'),  pi_prev).build())
            b.addAction(NotificationAction(_icon_res, String('Pause'), pi_pause).build())
            b.addAction(NotificationAction(_icon_res, String('Next'),  pi_next).build())
            b.setStyle(style)
            b.setVisibility(1)   # VISIBILITY_PUBLIC
            b.setOngoing(True)

            try:
                notif = b.build()
                nm.notify(2, notif)
                Logger.info("App: Fallback activity notification posted successfully")
                toast("NOTIF ACTIVADA")
            except Exception as inner_e:
                Logger.error(f"App: nm.notify failed: {inner_e}")
                toast(f"ERROR NOTIF: {inner_e}")
        except Exception as e:
            Logger.error(f"App: Fallback notification failed: {e}")

    def update_activity_notification(self, title, artist, duration=0, position=0, state='playing'):
        """Update the fallback notification (built from Activity) with current song info."""
        if platform != "android": return
        setup_jni_globals()
        try:
            from jnius import autoclass # type: ignore
            from android import api_version  # type: ignore
            
            # Cast python numbers to longs for Android API (ms)
            l_duration = int(duration * 1000)
            l_position = int(position * 1000)

            R_drawable = autoclass('android.R$drawable')
            NotificationBuilder = autoclass('android.app.Notification$Builder')
            NotificationAction = autoclass('android.app.Notification$Action$Builder')
            MediaStyle = autoclass('android.app.Notification$MediaStyle')

            ch = self._notif_channel
            mActivity = self._notif_activity
            pi = self._notif_pi

            style = MediaStyle()
            style.setMediaSession(self._media_session_act.getSessionToken())
            style.setShowActionsInCompactView(0, 1, 2)

            # Resolve mipmap icon (re-resolved each call for safety)
            _r = mActivity.getResources()
            _p = mActivity.getPackageName()
            _ico = _r.getIdentifier('icon', 'mipmap', _p) or autoclass('android.R$drawable').ic_media_play

            # Cast strings to CharSequence to avoid Jnius constructor matching issues
            
            if api_version >= 26:
                b = NotificationBuilder(mActivity, String(ch))
            else:
                b = NotificationBuilder(mActivity)
            
            b.setContentTitle(String(title))
            b.setContentText(String(artist))
            b.setSmallIcon(_ico)  # FIX: mipmap resource
            b.addAction(NotificationAction(_ico, String('Prev'), pi['prev']).build())

            if state == 'playing':
                b.addAction(NotificationAction(_ico, String('Pause'), pi['pause']).build())
            else:
                b.addAction(NotificationAction(_ico, String('Play'),  pi['play']).build())

            b.addAction(NotificationAction(_ico, String('Next'), pi['next']).build())
            b.setStyle(style)
            b.setVisibility(1)
            b.setOngoing(True)

            self._notif_nm.notify(2, b.build())

            # Also update MediaSession metadata and PlaybackState for lockscreen
            try:
                # Update State
                ps_builder = autoclass('android.media.session.PlaybackState$Builder')()
                # Actions: PLAY(4), PAUSE(2), NEXT(32), PREV(16), SEEK(256), PLAY_PAUSE(512) = 822
                ps_builder.setActions(822)
                # Cast strings to CharSequence to avoid Jnius constructor matching issues
                    
                # Use icon resources from the app or system
                icon_play = 17301540  # android.R.drawable.ic_media_play
                icon_pause = 17301539 # android.R.drawable.ic_media_pause
                icon_prev = 17301541  # android.R.drawable.ic_media_previous
                icon_next = 17301538  # android.R.drawable.ic_media_next

                # Build Actions
                action_prev = NotificationAction.Builder(icon_prev, String("Prev"), pi['prev']).build()
                action_play = NotificationAction.Builder(
                    icon_play if state != 'playing' else icon_pause,
                    String("Play/Pause"),
                    pi['play'] if state != 'playing' else pi['pause']
                ).build()
                action_next = NotificationAction.Builder(icon_next, String("Next"), pi['next']).build()

                state_int = 3 if state == 'playing' else 2 # PLAYING=3, PAUSED=2
                ps_builder.setState(state_int, l_position, 1.0)
                self._media_session_act.setPlaybackState(ps_builder.build())

                # Update Metadata
                MediaMetadataBuilder = autoclass('android.media.MediaMetadata$Builder')
                meta = MediaMetadataBuilder()
                meta.putString(String('android.media.metadata.TITLE'),  String(title))
                meta.putString(String('android.media.metadata.ARTIST'), String(artist))
                meta.putLong(String('android.media.metadata.DURATION'), l_duration)
                self._media_session_act.setMetadata(meta.build())
                # Syncing state again after metadata (helps Android 14 UI)
                self._media_session_act.setPlaybackState(ps_builder.build())
            except Exception: pass
        except Exception as e:
            Logger.warning(f"App: update_activity_notification failed: {e}")

    def _setup_media_receiver(self):
        """Sets up a BroadcastReceiver on the Android UI Thread with robust JNI calls"""
        if platform != 'android': return
        from android.runnable import run_on_ui_thread # type: ignore

        @run_on_ui_thread
        def _do_register():
            Logger.info("App: Inside _setup_media_receiver (UI Thread)")
            try:
                from android import api_version, mActivity # type: ignore
                from jnius import autoclass # type: ignore
                
                Logger.info("App: Creating MediaActionReceiver proxy...")
                self._media_receiver = MediaActionReceiver(self)
                
                IntentFilter = autoclass('android.content.IntentFilter')
                ifilter = IntentFilter()
                ifilter.addAction("org.test.musicplayeryt.ACTION_PLAY")
                ifilter.addAction("org.test.musicplayeryt.ACTION_PAUSE")
                ifilter.addAction("org.test.musicplayeryt.ACTION_NEXT")
                ifilter.addAction("org.test.musicplayeryt.ACTION_PREV")
                
                Context = autoclass('android.content.Context')
                # RECEIVER_EXPORTED = 2. Required for cross-process intents on Android 14+
                flags = int(getattr(Context, 'RECEIVER_EXPORTED', 2))
                
                Logger.info(f"App: Registering receiver (API {api_version}) with flags {flags}...")
                
                # Use the Application Context to avoid Activity lifecycle leaks
                app_context = mActivity.getApplicationContext()
                
                if api_version >= 33:
                    # Explicitly using the context to avoid signature issues on PythonActivity
                    app_context.registerReceiver(self._media_receiver, ifilter, flags)
                else:
                    app_context.registerReceiver(self._media_receiver, ifilter)
                
                Logger.info("App: MediaActionReceiver successfully registered")
            except Exception as e:
                Logger.error(f"App: Failed to setup media receiver: {e}")
        
        _do_register()

    def update_service_metadata(self, state="playing"):
        """Broadcasts current song metadata to the background service"""
        if platform != "android" or self.current_index == -1 or not self.current_playlist:
            return
            
        try:
            from jnius import autoclass # type: ignore
            Intent = autoclass('android.content.Intent')
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            mActivity = PythonActivity.mActivity
            
            intent = Intent("org.test.musicplayeryt.UPDATE_METADATA")
            # FIX (Android 14): explicit package is required for cross-process broadcasts.
            # Without setPackage(), Android 14 silently drops implicit broadcasts
            # directed at a separate process (the :service_playback process).
            intent.setPackage(mActivity.getPackageName())
            
            current_song = self.current_playlist[self.current_index]
            title = current_song.get('title', 'Unknown')
            artist = current_song.get('artist', 'Unknown')
            
            intent.putExtra("title", title)
            intent.putExtra("artist", artist)
            intent.putExtra("state", state)
            
            mActivity.sendBroadcast(intent)
            Logger.info(f"App: Metadata broadcast sent — title={title!r} state={state!r}")
        except Exception as e:
            Logger.warning(f"App: Failed to broadcast metadata: {e}")

    def _fetch_recommendations_thread(self):
        recs = get_recommendations()
        self.recommendations_cache = recs  # Cache recommendations for back button
        self._update_results_rv(recs, "RECOMENDADOS PARA TI")

    def go_to_library(self):
        self.root.transition = SlideTransition(direction="right")
        self.root.current = "library"

    def go_to_offline(self):
        self.root.transition = SlideTransition(direction="left")
        self.root.current = "offline"
        self.load_offline_songs()

    def go_to_player(self):
        if self.current_index != -1:
            self.root.transition = SlideTransition(direction="up")
            self.root.current = "player"
        else:
            toast("Nada en reproducción")

    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        btn = self.root.get_screen("player").ids.shuffle_btn
        btn.text_color = "#BB86FC" if self.is_shuffle else "#444444"
        toast("Aleatorio: ON" if self.is_shuffle else "Aleatorio: OFF")

    def toggle_repeat(self):
        self.is_repeat = not self.is_repeat
        btn = self.root.get_screen("player").ids.repeat_btn
        btn.text_color = "#BB86FC" if self.is_repeat else "#444444"
        toast("Repetir: ON" if self.is_repeat else "Repetir: OFF")

    def open_file_manager(self):
        self.file_manager.show(self.music_path)
        self.manager_open = True

    def select_path(self, path):
        self.music_path = path
        self.exit_manager()
        toast(f"Carpeta: {os.path.basename(path)}")
        self.load_offline_songs()

    def exit_manager(self, *args):
        self.file_manager.close()
        self.manager_open = False

    def search_songs(self, query):
        if not query: return
        
        # Track search mode
        self.library_mode = 'search'
        
        # UI State - Instant feedback
        self.root.get_screen("library").ids.search_spinner.active = True
        
        if query not in self.search_history:
            self.search_history.insert(0, query)
            self.search_history = self.search_history[:5]
            
        # Concurrency: Use threading to avoid blocking main loop
        threading.Thread(target=self._search_songs_thread, args=(query,), daemon=True).start()

    @mainthread
    def _update_results_rv(self, results, title):
        """Thread-safe UI update using RecycleView.data"""
        lib_ids = self.root.get_screen("library").ids
        lib_ids.search_spinner.active = False
        lib_ids.list_header.text = title
        
        self.last_results = results
        
        # Map raw results to SearchItem properties
        rv_data = []
        for i, res in enumerate(results):
            rv_data.append({
                'title': str(res.get('title', 'Unknown'))[:55],
                'artist': res.get('artist', 'YouTube'),
                'thumbnail': res.get('thumbnails', [{}])[0].get('url', '') if res.get('thumbnails') else '',
                'index': i,
                'song_data': res,
                'is_playlist_view': False
            })
        
        lib_ids.results_rv.data = rv_data
        
        if not results and "RESULTADOS" in title:
            toast("Sin resultados")

    def load_offline_songs(self):
        # Track offline mode
        self.library_mode = 'offline'
        # Scan for local music in thread
        threading.Thread(target=self._load_offline_thread, daemon=True).start()

    def _load_offline_thread(self):
        path = self.music_path
        try:
            if not os.path.exists(path):
                os.makedirs(path, exist_ok=True)
            elif not os.path.isdir(path):
                path = os.path.dirname(path)
        except Exception as e:
            Logger.error(f"App: Error accessing directory {path}: {e}")
            return
            
        files = [f for f in os.listdir(path) if f.endswith(('.mp3', '.m4a', '.webm', '.opus', '.ogg'))]
        
        # Schedule UI update
        Clock.schedule_once(lambda dt: self._display_offline_results(files, path))

    @mainthread
    def _display_offline_results(self, files, path):
        offline_rv = self.root.get_screen("offline").ids.offline_rv
        self.offline_playlist = []
        rv_data = []
        
        for i, filename in enumerate(files):
            full_path = os.path.join(path, filename)
            song_data = {'title': filename, 'url': full_path, 'artist': 'Local', 'thumbnails': []}
            self.offline_playlist.append(song_data)
            
            rv_data.append({
                'title': filename[:50],
                'artist': "Audio Local",
                'index': i,
                'song_data': song_data,
                'is_playlist_view': False # Default for offline songs
            })
        
        offline_rv.data = rv_data
        
        if not files:
            toast("No hay música descargada")

    def play_local_song(self, index):
        """Play a locally downloaded song from the offline playlist"""
        if not self.player:
            toast("Motor de audio no listo")
            return
            
        if index < 0 or index >= len(self.offline_playlist):
            Logger.error("App: Local play index out of range")
            return

        data = self.offline_playlist[index]
        self.current_playlist = self.offline_playlist
        self.current_index = index
        
        # Switch to player screen immediately
        self.root.transition = SlideTransition(direction="up")
        self.root.current = "player"
        
        # Validate path
        path = data['url']
        if not path or not os.path.exists(path):
            Logger.error(f"App: Local file not found: {path}")
            self._on_playback_error("Archivo local no encontrado")
            return

        # Prepare UI
        player_screen = self.root.get_screen("player")
        player_screen.ids.song_title.text = data['title']
        player_screen.ids.artist_name.text = "Local"
        player_screen.ids.play_pause_btn.icon = "pause-circle"
        player_screen.ids.loading_spinner.active = True # Show loading while opening file

        # Run playback in background thread (SoundLoader can block)
        threading.Thread(target=self._playback_thread, args=(path,), daemon=True).start()

    def delete_downloaded_song(self, path):
        """Elimina un MP3 localmente del dispositivo de almacenamiento."""
        if not path:
            return
        try:
            if os.path.exists(path):
                os.remove(path)
                toast("Audio eliminado del dispositivo")
            else:
                toast("El archivo ya no existe")
            # Refrescar la vista inmediatamente
            self.load_offline_songs()
        except Exception as e:
            Logger.error(f"App: Error deleting local audio: {e}")
            toast(f"No se pudo eliminar: {str(e)[:30]}")

    def _search_songs_thread(self, query):
        """Background thread for network search with user-friendly error handling."""
        try:
            results = search_youtube(query)
            if results:
                self._update_results_rv(results, f"RESULTADOS: {query.upper()}")
            else:
                Clock.schedule_once(lambda dt: toast("Sin resultados para esta búsqueda"))
                self._update_results_rv([], f"SIN RESULTADOS: {query.upper()}")
        except Exception as e:
            error_str = str(e).lower()
            Logger.error(f"App: Search thread failed: {e}")
            
            # Classify the error for the user
            if any(k in error_str for k in ('timeout', 'timed out', 'socket', 'connection', 'network', 'unreachable')):
                Clock.schedule_once(lambda dt: toast("Sin conexión — revisa tu WiFi o Datos"))
            elif 'sign in' in error_str or '403' in error_str or 'bot' in error_str:
                Clock.schedule_once(lambda dt: toast("YouTube bloqueó la búsqueda, intenta de nuevo"))
            else:
                Clock.schedule_once(lambda dt: toast("Error al buscar — inténtalo de nuevo"))
            
            self._update_results_rv([], "ERROR DE CONEXIÓN")

    def play_selected_song(self, index):
        if not self.player:
            toast("Motor de audio no disponible")
            return
            
        self.current_playlist = self.last_results
        self.current_index = index
        data = self.current_playlist[self.current_index]
        
        # Show Loading on Player Screen
        self.root.transition = SlideTransition(direction="up")
        self.root.current = "player"
        player_screen = self.root.get_screen("player")
        player_screen.ids.loading_spinner.active = True
        player_screen.ids.song_title.text = "Cargando..."
        player_screen.ids.artist_name.text = data.get('artist', 'YouTube')
        
        # Optimization: Use ThreadPoolExecutor
        self.executor.submit(self._prepare_playback_thread, data)

    @mainthread
    def display_playlists(self):
        playlists_rv = self.root.get_screen("playlists").ids.playlists_rv
        rv_data = []
        
        for name in self.playlists.keys():
            rv_data.append({
                'text': name,
                'playlist_name': name
            })
        
        playlists_rv.data = rv_data

    def open_playlist(self, name):
        try:
            self.current_playlist_name = name
            self.library_mode = 'playlist'
            songs = self.playlists.get(name, [])
            if not isinstance(songs, list):
                Logger.error(f"App: Corrupt playlist data for {name}")
                songs = []
            
            self.root.transition = SlideTransition(direction="left")
            self.root.current = "library"
            # Offload heavy UI preparation to thread to prevent ANR
            threading.Thread(target=self._prepare_playlist_view_thread, args=(name, songs), daemon=True).start()
        except Exception as e:
            Logger.error(f"App: Error opening playlist: {e}")
            toast("Error al abrir playlist")

    def _prepare_playlist_view_thread(self, playlist_name, songs):
        """Prepare RecycleView data without blocking main thread"""
        try:
            self.last_results = songs
            rv_data = []
            for i, res in enumerate(songs):
                rv_data.append({
                    'title': str(res.get('title', 'Unknown'))[:55],
                    'artist': str(res.get('artist', 'YouTube')),
                    'thumbnail': res.get('thumbnails', [{}])[0].get('url', '') if res.get('thumbnails') else '',
                    'index': i,
                    'song_data': res,
                    'is_playlist_view': True
                })
            Clock.schedule_once(lambda dt: self.display_playlist_songs(playlist_name, songs, rv_data))
        except Exception as e:
            Logger.error(f"App: Error parsing playlist data: {e}")

    def create_playlist_dialog(self):
        self.dialog_input = MDTextField(hint_text="Nombre de la playlist")
        self.playlist_dialog = MDDialog(
            title="Nueva Playlist",
            type="custom",
            content_cls=self.dialog_input,
            buttons=[
                MDFlatButton(text="CANCELAR", on_release=lambda x: self.playlist_dialog.dismiss()),
                MDFlatButton(text="CREAR", on_release=lambda x: self.create_playlist(self.dialog_input.text))
            ],
        )
        self.playlist_dialog.open()

    def create_playlist(self, name):
        if not name: return
        if name not in self.playlists:
            self.playlists[name] = []
            self.save_playlists_data()
            self.display_playlists()
            toast(f"Playlist '{name}' creada")
        self.playlist_dialog.dismiss()

    def add_song_to_playlist_dialog(self, song_data):
        if not self.playlists:
            toast("Crea una playlist primero")
            return

        content = MDList()
        for name in self.playlists.keys():
            item = OneLineListItem(text=name, on_release=lambda x, n=name: self.add_song_to_playlist(song_data, n))
            content.add_widget(item)
        
        scroll = ScrollView(size_hint_y=None, height=dp(200))
        scroll.add_widget(content)
        
        self.add_dialog = MDDialog(
            title="Añadir a Playlist",
            type="custom",
            content_cls=scroll,
        )
        self.add_dialog.open()

    def add_song_to_playlist(self, song_data, playlist_name):
        if playlist_name in self.playlists:
            # Evitar duplicados
            if any(s['url'] == song_data['url'] for s in self.playlists[playlist_name]):
                toast("Ya está en la playlist")
            else:
                self.playlists[playlist_name].append(song_data)
                self.save_playlists_data()
                toast(f"Añadido a {playlist_name}")
        self.add_dialog.dismiss()

    @mainthread
    def display_playlist_songs(self, playlist_name, songs, rv_data=None):
        """Display songs from a playlist using RecycleView"""
        try:
            lib_ids = self.root.get_screen("library").ids
            lib_ids.search_spinner.active = False
            lib_ids.list_header.text = f"PLAYLIST: {str(playlist_name).upper()}"
            
            if rv_data is not None:
                lib_ids.results_rv.data = rv_data
            
            if not songs:
                toast("La playlist está vacía")
        except Exception as e:
            Logger.error(f"App: UI error rendering playlist: {e}")

    def delete_song_from_playlist(self, playlist_name, song_url, callback=None):
        """Delete a song from a playlist"""
        if playlist_name in self.playlists:
            # Find and remove the song by URL
            self.playlists[playlist_name] = [
                s for s in self.playlists[playlist_name]
                if s['url'] != song_url
            ]
            self.save_playlists_data()
            toast("Canción eliminada de la playlist")
            
            # Refresh the display
            if callback:
                callback()
            else:
                self.display_playlists()

    def on_item_right_button(self, item):
        """Helper to handle RightButton action based on view context"""
        if item.is_playlist_view:
            self.delete_song_from_playlist(
                self.current_playlist_name, 
                item.song_data['url'], 
                lambda: self.display_playlist_songs(self.current_playlist_name, self.playlists.get(self.current_playlist_name, []))
            )
        else:
            self.add_song_to_playlist_dialog(item.song_data)

    def delete_playlist(self, playlist_name):
        """Elimina una playlist entera junto con todas sus canciones"""
        if playlist_name in self.playlists:
            del self.playlists[playlist_name]
            self.save_playlists_data()
            toast(f"Playlist '{playlist_name}' eliminada")
            self.display_playlists()

    def get_current_song_data(self):
        if self.current_index != -1 and self.current_playlist:
            return self.current_playlist[self.current_index]
        return {}

    def download_song(self):
        """Definitive native Android download initiator with runtime permissions."""
        if self.current_index == -1 or not self.current_playlist:
            toast("Nada seleccionado")
            return

        if platform == 'android':
            try:
                from android.permissions import request_permissions, Permission  # type: ignore
                from android import api_version # type: ignore
                
                perms = []
                if api_version >= 33:
                    # Android 13+ auto-denies WRITE_EXTERNAL_STORAGE without a popup.
                    # We just need READ_MEDIA_AUDIO for metadata, writing to public Download is allowed automatically.
                    perms.append(Permission.READ_MEDIA_AUDIO)
                else:
                    perms.append(Permission.WRITE_EXTERNAL_STORAGE)
                    perms.append(Permission.READ_EXTERNAL_STORAGE)
                    
                request_permissions(perms, self._on_download_permission_result)
            except Exception as e:
                Logger.error(f"App: Permission request failed: {e}")
                toast(f"Error de permisos: {str(e)[:40]}")
        else:
            # On Desktop/Linux, go directly to download
            self._start_download_thread()

    @mainthread
    def _on_download_permission_result(self, permissions, grants):
        """Callback from Android runtime permission dialog."""
        if all(grants):
            Logger.info("App: Storage permissions granted — starting download")
            Clock.schedule_once(lambda dt: self._start_download_thread(), 0)
        else:
            denied = [p for p, g in zip(permissions, grants) if not g]
            Logger.warning(f"App: Permissions denied: {denied}")
            toast("Permiso de almacenamiento denegado")

    def _start_download_thread(self):
        try:
            data = self.current_playlist[self.current_index]
            title = data.get('title', 'Unknown_Song')
            display_title = str(title)[:25]
            toast(f"Descargando: {display_title}...")
            t = threading.Thread(target=self._download_thread, args=(data,), daemon=True)
            t.start()
        except Exception as e:
            Logger.error(f"App: Error starting download thread: {e}")
            toast(f"Fallo al iniciar: {str(e)[:40]}")

    def _download_thread(self, data):
        """Background download. Uses primary_external_storage_path() on Android (the only valid public path)."""
        try:
            path = None

            if platform == 'android':
                try:
                    # Kivy's own native helper — guaranteed to return the real SD card path
                    from android.storage import primary_external_storage_path  # type: ignore
                    ext_path = primary_external_storage_path()
                    path = os.path.join(ext_path, 'Download', 'ReproductorGolomn')
                    Logger.info(f"App: Using Android external path: {path}")
                except Exception as e:
                    Logger.error(f"App: primary_external_storage_path() failed: {e}")

            # Safe fallback: internal app storage (always writable, no permissions needed)
            if not path:
                path = os.path.join(MDApp.get_running_app().user_data_dir, 'downloads')
                Logger.warning(f"App: Falling back to internal path: {path}")

            try:
                os.makedirs(path, exist_ok=True)
            except Exception as e:
                Logger.error(f"App: Cannot create download directory: {e}")
                # Last resort fallback
                path = MDApp.get_running_app().user_data_dir
                os.makedirs(path, exist_ok=True)

            url = data.get('url')
            if not url:
                Clock.schedule_once(lambda dt: toast("Error: URL no válida"))
                return

            Logger.info(f"App: Starting download to {path}")
            success, message = download_audio(url, path)

            if success:
                Clock.schedule_once(lambda dt: toast(f"✓ Guardado en Downloads/ReproductorGolomn"))
            else:
                Logger.error(f"App: Download failed: {message}")
                Clock.schedule_once(lambda dt: toast(f"✗ Error: {str(message)[:40]}"))

        except Exception as e:
            Logger.error(f"App: Critical error in download thread: {e}")
            Clock.schedule_once(lambda dt: toast(f"Error fatal: {str(e)[:40]}"))

    def _prepare_playback_thread(self, data):
        video_url = data.get('url')
        video_id = data.get('id') or video_url
        
        # 1. Check Cache
        if video_id in self.url_cache:
            Logger.info(f"App: Using cached URL for {video_id[:15]}")
            audio_url, title, thumbnail, artist, _ = self.url_cache[video_id]
            Clock.schedule_once(lambda dt: self._start_playback(audio_url, title, thumbnail, artist))
            return

        # 2. Extract
        try:
            audio_url, title, thumbnail, artist = get_audio_url(video_url)
            if audio_url:
                # Store in Cache
                self.url_cache[video_id] = (audio_url, title, thumbnail, artist, Clock.get_time())
                Clock.schedule_once(lambda dt: self._start_playback(audio_url, title, thumbnail, artist))
            else:
                Clock.schedule_once(lambda dt: self._on_playback_error("No se encontró el audio"))
        except Exception as e:
            Logger.error(f"App: Error en prepare_playback: {e}")
            Clock.schedule_once(lambda dt: self._on_playback_error(str(e)))

    def _on_playback_error(self, message):
        player_screen = self.root.get_screen("player")
        player_screen.ids.loading_spinner.active = False
        
        # NOTE: We do not overwrite song_title.text here anymore because if a non-fatal 
        # network warning fires, we don't want the UI to be permanently stuck on "Error".
        
        MDSnackbar(
            MDLabel(
                text=f"Error: {message[:50]}",
                theme_text_color="Custom",
                text_color="#BB86FC",
            ),
            md_bg_color="#121212",
        ).open()

    def _start_playback(self, url, title, thumbnail_url, artist):
        player_screen = self.root.get_screen("player")
        player_screen.ids.loading_spinner.active = False
        player_screen.ids.song_title.text = title
        player_screen.ids.artist_name.text = artist
        if thumbnail_url:
            try: 
                player_screen.ids.thumbnail.source = thumbnail_url
            except Exception as e:
                Logger.warning(f"App: Thumbnail load error: {e}")
        
        if not self.player:
            self._on_playback_error("Motor de audio no disponible")
            return
        
        # Validate URL before playing
        if not url or not url.startswith(('http://', 'https://')):
            Logger.error(f"App: Invalid URL format: {url[:50] if url else 'None'}")
            self._on_playback_error("URL de audio inválida")
            return
        
        try:
            Logger.info(f"App: Starting playback with URL length: {len(url)}")
            # Add small delay to ensure UI updates
            Clock.schedule_once(lambda dt: self._do_playback(url), 0.1)
        except Exception as e:
            Logger.error(f"App: Playback scheduling error: {e}")
            self._on_playback_error(f"Error al reproducir: {str(e)[:50]}")
    
    def _do_playback(self, url):
        """Ejecutar la reproducción en thread separado para no bloquear UI"""
        try:
            player_screen = self.root.get_screen("player")
            
            # Initial Notification Update for Lockscreen
            if platform == 'android' and self.current_index >= 0:
                song = self.current_playlist[self.current_index]
                self.update_activity_notification(song['title'], song['artist'], state='playing')
            # Run play() in separate thread to avoid blocking UI
            def safe_play(u):
                if not self.player:
                    return
                try:
                    self.player.play(u)
                except Exception as pe:
                    Logger.error(f"App: Playback crash prevented: {pe}")
                    err_msg = str(pe)
                    toast(f"Error de audio: {err_msg}")
                    self._on_playback_error(f"Fallo nativo: {err_msg}")

            threading.Thread(
                target=self._playback_thread,
                args=(url, safe_play),
                daemon=True
            ).start()
        except Exception as e:
            Logger.error(f"App: Play Error: {e}")
            self._on_playback_error(f"Fallo al reproducir: {str(e)[:50]}")
            return
    
    def _playback_thread(self, url, play_func=None):
        """Thread worker for playback (SoundLoader.load is blocking)"""
        try:
            if play_func:
                play_func(url)
            elif self.player:
                self.player.play(url)
            
            player_screen = self.root.get_screen("player")
            def update_icon(dt):
                player_screen.ids.play_pause_btn.icon = "pause-circle"
            Clock.schedule_once(update_icon, 0)
            Logger.info("App: Playback initiated successfully")
        except Exception as e:
            err_msg = str(e)
            Logger.error(f"App: Playback thread error: {e}")
            Clock.schedule_once(lambda dt: self._on_playback_error(f"Fallo: {err_msg[0:50]}"), 0)
        
        # Pulse & Glow Animation
        try:
            if self.pulse_anim: 
                self.pulse_anim.cancel(self)
            self.pulse_anim = Animation(album_scale=1.03, title_glow=0.6, duration=1, t='in_out_quad') + \
                             Animation(album_scale=1.0, title_glow=1.0, duration=1, t='in_out_quad')
            self.pulse_anim.repeat = True
            self.pulse_anim.start(self)
        except Exception as e:
            Logger.warning(f"App: Animation error: {e}")

        if self.update_event:
            self.update_event.cancel()
        self.update_event = Clock.schedule_interval(self._update_ui, 0.5)
        # FIX (race condition): Delay metadata broadcast by 2s.
        # The service's MetadataReceiver takes ~1-2s to register after startForeground().
        # Sending the broadcast immediately means it arrives before the receiver exists
        # and gets silently dropped by Android. The 2s delay ensures the receiver is ready.
        Clock.schedule_once(lambda dt: self.update_service_metadata("playing"), 2.0)
        # Also update fallback activity notification (covers case where service failed to start)
        if self.current_index >= 0 and self.current_playlist:
            song = self.current_playlist[self.current_index]
            self.update_activity_notification(song.get('title', ''), song.get('artist', ''), state='playing')

    def on_next(self):
        if not self.player: return
        if not self.current_playlist: return
        
        if self.is_repeat:
            # Stay on same song
            pass
        elif self.is_shuffle:
            self.current_index = random.randint(0, len(self.current_playlist)-1)
        else:
            self.current_index = (self.current_index + 1) % len(self.current_playlist)
            
        self.play_selected_song(self.current_index)

    def on_previous(self):
        if not self.player: return
        if not self.current_playlist: return
        self.current_index = (self.current_index - 1) % len(self.current_playlist)
        self.play_selected_song(self.current_index)

    def _update_ui(self, dt):
        if not self.player or self.is_seeking:
            return
        
        # Throttling for notification updates (every ~1.5s assuming dt=0.5)
        if not hasattr(self, '_notif_update_counter'):
            self._notif_update_counter = 0
        self._notif_update_counter += 1
        
        try:
            length = self.player.get_length() if self.player else 0
            current = self.player.get_time() if self.player else 0
            
            if length > 0:
                progress = (current / length) * 100
                player_screen = self.root.get_screen("player")
                player_screen.ids.progress_slider.value = progress
                player_screen.ids.current_time_label.text = self._format_time(current)
                player_screen.ids.total_time_label.text = self._format_time(length)
                
                # Update Android Lockscreen Progress
                if platform == 'android' and self._notif_update_counter % 3 == 0:
                    song = self.current_playlist[self.current_index]
                    self.update_activity_notification(
                        song['title'], song['artist'],
                        duration=length/1000.0, position=current/1000.0,
                        state='playing' if self.player.is_playing() else 'paused'
                    )
                
                # Pre-fetch logic (85% through)
                if progress > 85 and self.current_playlist:
                    self._check_pre_fetch()
                
                if current >= length - 1500 and length > 5000:
                    if self.is_repeat:
                        self.player.set_time(0)
                        self.player.play()
                    else:
                        self.on_next()
                    if self.update_event:
                        self.update_event.cancel()
                        self.update_event = None
        except Exception as e:
            Logger.debug(f"App: _update_ui error (non-critical): {e}")

    def _check_pre_fetch(self):
        """Analyze if we should pre-fetch the next song in the background"""
        if not self.current_playlist or len(self.current_playlist) < 1: 
            return
        
        # Determine next index
        next_idx = self.current_index
        if self.is_repeat: 
            return
        elif self.is_shuffle: 
            # In shuffle, next is random, hard to pre-fetch unless we have a queue
            return 
        else: 
            next_idx = (self.current_index + 1) % len(self.current_playlist)
        
        next_data = self.current_playlist[next_idx]
        next_id = next_data.get('id') or next_data.get('url')
        
        if next_id != self.pre_fetched_id and next_id not in self.url_cache:
            self.pre_fetched_id = next_id
            Logger.info(f"App: Pre-fetching next song metadata: {next_id[:15]}")
            self.executor.submit(self._do_pre_fetch, next_data)

    def _do_pre_fetch(self, data):
        """Background task for URL extraction"""
        try:
            video_url = data.get('url')
            video_id = data.get('id') or video_url
            # Small delay to not compete with UI
            import time
            time.sleep(1)
            audio_url, title, thumbnail, artist = get_audio_url(video_url)
            if audio_url:
                self.url_cache[video_id] = (audio_url, title, thumbnail, artist, Clock.get_time())
                Logger.info(f"App: Pre-fetch success for {video_id[:15]}")
        except: 
            pass

    def _format_time(self, ms):
        seconds = int((ms / 1000) % 60)
        minutes = int((ms / (1000 * 60)) % 60)
        return f"{minutes:02d}:{seconds:02d}"

    def toggle_playback(self):
        if not self.player:
            toast("Motor de audio no disponible")
            return
        player_screen = self.root.get_screen("player")
        if self.player.is_playing():
            self.player.pause()
            self.update_service_metadata("paused")
            player_screen.ids.play_pause_btn.icon = "play-circle"
            if self.pulse_anim: self.pulse_anim.cancel(self)
            if self.current_index >= 0 and self.current_playlist:
                s = self.current_playlist[self.current_index]
                self.update_activity_notification(
                    s.get('title', ''), s.get('artist', ''),
                    duration=self.player.get_length()/1000.0,
                    position=self.player.get_time()/1000.0,
                    state='paused'
                )
        else:
            self.player.resume() 
            self.update_service_metadata("playing")
            player_screen.ids.play_pause_btn.icon = "pause-circle"
            if self.pulse_anim: self.pulse_anim.start(self)
            if self.current_index >= 0 and self.current_playlist:
                s = self.current_playlist[self.current_index]
                self.update_activity_notification(
                    s.get('title', ''), s.get('artist', ''),
                    duration=self.player.get_length()/1000.0,
                    position=self.player.get_time()/1000.0,
                    state='playing'
                )

    def seek_media(self, value):
        """Native seek without manual blocking, highly fluid."""
        if not self.player:
            return

        try:
            length = self.player.get_length()

            if length <= 0:
                Logger.warning("App: Seek blocked — stream has no known duration (live/broken)")
                toast("No se puede adelantar")
                return

            target_ms = int((value / 100) * length)
            Logger.info(f"App: Seek requested to {target_ms}ms of {length}ms")

            # Native set_time already handles thread-safe buffering directly in Java
            self.player.set_time(target_ms)
            
            # Instantly update Kivy UI clock to feel deeply responsive (no ghost bouncing)
            player_screen = self.root.get_screen("player")
            player_screen.ids.current_time_label.text = self._format_time(target_ms)

        except Exception as e:
            Logger.error(f"App: Seek Error: {e}")
            toast(f"Error al adelantar: {str(e)}")
    
    def seek_relative(self, seconds):
        """Seek forward or backward by seconds"""
        if not self.player:
            return
        
        try:
            current = self.player.get_time()
            new_time = max(0, current + (seconds * 1000))
            self.player.set_time(int(new_time))
            Logger.info(f"App: Relative seek by {seconds}s to {new_time}ms")
            
            # Update UI immediately for maximum fluidity
            length = self.player.get_length()
            if length > 0:
                player_screen = self.root.get_screen("player")
                player_screen.ids.progress_slider.value = (new_time / length) * 100
                player_screen.ids.current_time_label.text = self._format_time(new_time)
        except Exception as e:
            Logger.error(f"App: Relative seek error: {e}")

def toast(message):
    """Muestra un mensaje flotante (Toast) en Android o MDToast en Desktop"""
    if platform == 'android':
        try:
            from jnius import autoclass
            from android.runnable import run_on_ui_thread # type: ignore
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            Toast = autoclass('android.widget.Toast')
            String = autoclass('java.lang.String')
            context = PythonActivity.mActivity
            
            @run_on_ui_thread
            def show_native_toast():
                try:
                    Toast.makeText(context, String(message), Toast.LENGTH_SHORT).show()
                except Exception:
                    pass
                    
            show_native_toast()
        except Exception as e:
            Logger.warning(f"App: Toast nativo falló: {e}")
            from kivymd.toast import toast as md_toast
            md_toast(message)
    else:
        from kivymd.toast import toast as md_toast
        md_toast(message)

if __name__ == "__main__":
    MusicPlayerApp().run()
