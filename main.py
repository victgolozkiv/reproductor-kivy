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
else:
    Config.set('graphics', 'width', '1280')
    Config.set('graphics', 'height', '800')
    Config.set('graphics', 'resizable', '1')

import gc
import json

from kivy.lang import Builder
from kivy.properties import StringProperty, ObjectProperty, NumericProperty, BooleanProperty
from kivy.clock import Clock, mainthread
from kivy.core.window import Window
from kivy.animation import Animation
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.factory import Factory
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.anchorlayout import AnchorLayout
from kivy.uix.image import AsyncImage
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.graphics import Color, Line

from kivy.logger import Logger
from kivymd.app import MDApp
from kivymd.uix.filemanager import MDFileManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivy.uix.screenmanager import SlideTransition
from kivymd.uix.button import MDIconButton, MDFlatButton, MDFloatingActionButton
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
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.slider import MDSlider
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.fitimage import FitImage
from kivymd.uix.dialog import MDDialog
from kivymd.toast import toast
from kivymd.uix.snackbar import MDSnackbar
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.anchorlayout import MDAnchorLayout
from kivymd.uix.toolbar import MDTopAppBar

from extractor import get_audio_url, search_youtube, get_recommendations, download_audio
from player import get_best_player
from desktop_ui import get_desktop_ui

# Helper UI Classes
class ModernCard(MDCard):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#121212"
        self.radius = [dp(16)]
        self.elevation = 0
        self.padding = dp(12)
        self.spacing = dp(8)

class GlowingIconButton(MDIconButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_text_color = "Custom"
        self.text_color = "#BB86FC"
        self.user_font_size = "24sp"

class SectionTitle(MDLabel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_text_color = "Custom"
        self.text_color = "#FFFFFF"
        self.font_style = "H6"
        self.bold = True
        self.adaptive_height = True
        self.padding = [dp(16), dp(16), dp(16), dp(8)]

class SubsectionTitle(MDLabel):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.theme_text_color = "Custom"
        self.text_color = "#B3B3B3"
        self.font_style = "Body2"
        self.adaptive_height = True
        self.padding = [dp(16), dp(8), dp(16), dp(16)]

class MoodChip(MDFlatButton):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#1E1E1E"
        self.theme_text_color = "Custom"
        self.text_color = "#FFFFFF"
        self.font_style = "Caption"
        self.size_hint = (None, None)
        self.height = dp(36)
        self.padding = [dp(20), dp(8)]
        self.radius = [dp(18)]

class ModernSongCard(MDCard):
    thumbnail = StringProperty()
    title = StringProperty()
    artist = StringProperty()
    index = NumericProperty(0)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#0A0A0A"
        self.radius = [dp(12)]
        self.elevation = 0
        self.padding = 0
        self.spacing = 0
        
        layout = MDBoxLayout(orientation="vertical", spacing=dp(8))
        
        rel = RelativeLayout(size_hint_y=None, height=dp(160))
        self.card_thumbnail = FitImage(
            radius=[dp(12), dp(12), dp(12), dp(12)],
            allow_stretch=True,
            keep_ratio=False
        )
        rel.add_widget(self.card_thumbnail)
        
        play_btn = MDIconButton(
            icon="play-circle",
            theme_text_color="Custom",
            text_color="#BB86FC",
            user_font_size="48sp",
            pos_hint={"center_x": 0.5, "center_y": 0.5},
            md_bg_color=[0, 0, 0, 0.5],
            radius=[dp(24)],
            opacity=0.9
        )
        play_btn.bind(on_release=lambda x: MDApp.get_running_app().play_selected_song(self.index))
        rel.add_widget(play_btn)
        layout.add_widget(rel)
        
        info = MDBoxLayout(orientation="vertical", spacing=dp(4), padding=[dp(12), dp(8), dp(12), dp(12)], adaptive_height=True)
        self.title_label = MDLabel(
            theme_text_color="Custom",
            text_color="#FFFFFF",
            font_style="Subtitle2",
            bold=True,
            shorten=True,
            shorten_from="right",
            adaptive_height=True
        )
        self.artist_label = MDLabel(
            theme_text_color="Custom",
            text_color="#B3B3B3",
            font_style="Caption",
            shorten=True,
            adaptive_height=True
        )
        info.add_widget(self.title_label)
        info.add_widget(self.artist_label)
        layout.add_widget(info)
        self.add_widget(layout)
        
        self.bind(thumbnail=self._update_thumb, title=self._update_title, artist=self._update_artist)

    def _update_thumb(self, *args): self.card_thumbnail.source = self.thumbnail
    def _update_title(self, *args): self.title_label.text = self.title
    def _update_artist(self, *args): self.artist_label.text = self.artist

# UI Classes for RecycleView
class SearchItem(MDCard):
    title = StringProperty()
    artist = StringProperty()
    index = NumericProperty()
    thumbnail = StringProperty()
    song_data = ObjectProperty()
    is_playlist_view = BooleanProperty(False)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#0D0D0D"
        self.radius = [dp(12)]
        self.elevation = 2
        self.shadow_color = [0.737, 0.525, 0.988, 0.15]
        self.padding = [dp(12), dp(8)]
        self.spacing = dp(12)
        self.ripple_behavior = True
        
        layout = MDBoxLayout(orientation="horizontal", spacing=dp(12))
        
        self.thumb_card = MDCard(
            size_hint=(None, None),
            size=(dp(48), dp(48)),
            radius=[dp(8)],
            elevation=0,
            md_bg_color="#1A1A1A"
        )
        with self.thumb_card.canvas.before:
            self.border_color = Color(0.737, 0.525, 0.988, 0.1)
            self.border_line = Line(width=1.5, rounded_rectangle=(0, 0, dp(48), dp(48), 8))
        self.thumb_card.bind(pos=self._update_canvas, size=self._update_canvas)

        self.thumb_image = AsyncImage(
            size_hint=(1, 1),
            allow_stretch=True,
            keep_ratio=False
        )
        self.thumb_card.add_widget(self.thumb_image)
        layout.add_widget(self.thumb_card)
        
        info = MDBoxLayout(orientation="vertical", spacing=dp(2), size_hint_x=1)
        self.title_label = MDLabel(
            theme_text_color="Custom",
            text_color="#FFFFFF",
            font_size="15sp",
            bold=True,
            shorten=True,
            shorten_from="right",
            adaptive_height=True
        )
        self.artist_label = MDLabel(
            theme_text_color="Custom",
            text_color="#BB86FC",
            font_size="13sp",
            shorten=True,
            shorten_from="right",
            adaptive_height=True
        )
        info.add_widget(self.title_label)
        info.add_widget(self.artist_label)
        layout.add_widget(info)
        
        self.action_btn = MDIconButton(
            theme_text_color="Custom",
            user_font_size="20sp",
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            pos_hint={"center_y": 0.5}
        )
        self.action_btn.bind(on_release=lambda x: MDApp.get_running_app().on_item_right_button(self))
        layout.add_widget(self.action_btn)
        
        self.add_widget(layout)
        self.bind(title=self._update_ui, artist=self._update_ui, thumbnail=self._update_ui, is_playlist_view=self._update_ui)

    def _update_canvas(self, instance, value):
        self.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 8)

    def _update_ui(self, *args):
        self.title_label.text = self.title or "Sin título"
        self.artist_label.text = self.artist or "Artista"
        self.thumb_image.source = self.thumbnail or ""
        self.border_color.rgba = (0.737, 0.525, 0.988, 0.3) if self.is_playlist_view else (0.737, 0.525, 0.988, 0.1)
        self.action_btn.icon = "trash-can" if self.is_playlist_view else "playlist-plus"
        self.action_btn.text_color = "#BB86FC" if self.is_playlist_view else "#888888"

    def on_release(self):
        MDApp.get_running_app().play_selected_song(self.index)

class PlaylistItem(MDCard):
    text = StringProperty()
    playlist_name = StringProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#0D0D0D"
        self.radius = [dp(12)]
        self.elevation = 2
        self.shadow_color = [0.737, 0.525, 0.988, 0.2]
        self.padding = [dp(12), dp(10)]
        self.ripple_behavior = True
        
        layout = MDBoxLayout(orientation="horizontal", spacing=dp(12))
        
        icon_card = MDCard(
            size_hint=(None, None),
            size=(dp(44), dp(44)),
            radius=[dp(10)],
            elevation=0,
            md_bg_color="#BB86FC"
        )
        icon_card.add_widget(MDIcon(
            icon="playlist-music",
            theme_text_color="Custom",
            text_color="#000000",
            font_size="24sp",
            halign="center",
            valign="center"
        ))
        layout.add_widget(icon_card)
        
        info = MDBoxLayout(orientation="vertical", spacing=dp(2), size_hint_x=1, pos_hint={"center_y": 0.5})
        self.title_label = MDLabel(
            theme_text_color="Custom",
            text_color="#FFFFFF",
            font_size="16sp",
            bold=True,
            shorten=True,
            shorten_from="right",
            adaptive_height=True
        )
        info.add_widget(self.title_label)
        info.add_widget(MDLabel(
            text="Playlist",
            theme_text_color="Custom",
            text_color="#888888",
            font_size="12sp",
            adaptive_height=True
        ))
        layout.add_widget(info)
        
        del_btn = MDIconButton(
            icon="trash-can",
            theme_text_color="Custom",
            text_color="#FF4444",
            user_font_size="20sp",
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            pos_hint={"center_y": 0.5}
        )
        del_btn.bind(on_release=lambda x: MDApp.get_running_app().delete_playlist(self.text))
        layout.add_widget(del_btn)
        
        self.add_widget(layout)
        self.bind(text=self._update_text)

    def _update_text(self, *args):
        self.title_label.text = self.text

    def on_release(self):
        MDApp.get_running_app().open_playlist(self.text)

class OfflineItem(MDCard):
    title = StringProperty()
    artist = StringProperty()
    index = NumericProperty()
    song_data = ObjectProperty()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#0D0D0D"
        self.radius = [dp(12)]
        self.elevation = 2
        self.shadow_color = [0.737, 0.525, 0.988, 0.15]
        self.padding = [dp(12), dp(8)]
        self.ripple_behavior = True
        
        layout = MDBoxLayout(orientation="horizontal", spacing=dp(12))
        
        icon_card = MDCard(
            size_hint=(None, None),
            size=(dp(48), dp(48)),
            radius=[dp(8)],
            elevation=0,
            md_bg_color="#1A1A1A"
        )
        with icon_card.canvas.before:
            Color(0.737, 0.525, 0.988, 0.2)
            self.border_line = Line(width=1.5, rounded_rectangle=(0, 0, dp(48), dp(48), 8))
        icon_card.bind(pos=self._update_canvas, size=self._update_canvas)
        
        icon_card.add_widget(MDIcon(
            icon="music-note",
            theme_text_color="Custom",
            text_color="#BB86FC",
            font_size="24sp",
            halign="center",
            valign="center"
        ))
        layout.add_widget(icon_card)
        
        info = MDBoxLayout(orientation="vertical", spacing=dp(2), size_hint_x=1)
        self.title_label = MDLabel(
            theme_text_color="Custom",
            text_color="#FFFFFF",
            font_size="15sp",
            bold=True,
            shorten=True,
            shorten_from="right",
            adaptive_height=True
        )
        self.artist_label = MDLabel(
            theme_text_color="Custom",
            text_color="#888888",
            font_size="13sp",
            adaptive_height=True
        )
        info.add_widget(self.title_label)
        info.add_widget(self.artist_label)
        layout.add_widget(info)
        
        del_btn = MDIconButton(
            icon="trash-can",
            theme_text_color="Custom",
            text_color="#FF4444",
            user_font_size="20sp",
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            pos_hint={"center_y": 0.5}
        )
        del_btn.bind(on_release=lambda x: MDApp.get_running_app().delete_downloaded_song(self.song_data.get('url')))
        layout.add_widget(del_btn)
        
        self.add_widget(layout)
        self.bind(title=self._update_ui, artist=self._update_ui)

    def _update_canvas(self, instance, value):
        self.border_line.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 8)

    def _update_ui(self, *args):
        self.title_label.text = self.title or ""
        self.artist_label.text = self.artist or ""

    def on_release(self):
        MDApp.get_running_app().play_local_song(self.index)

# Screens for Mobile
class MobileScreenLibrary(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "library"
        self.md_bg_color = "#000000"
        
        main_layout = MDBoxLayout(orientation="vertical")
        
        self.ids['top_bar'] = MDTopAppBar(
            title="Mi Biblioteca",
            anchor_title="left",
            elevation=0,
            md_bg_color="#000000",
            specific_text_color="#FFFFFF"
        )
        self.ids['top_bar'].right_action_items = [
            ["playlist-music", lambda x: MDApp.get_running_app().go_to_playlists()],
            ["folder-music", lambda x: MDApp.get_running_app().go_to_offline()]
        ]
        main_layout.add_widget(self.ids['top_bar'])
        
        search_layout = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(60), padding=[dp(16), dp(8)])
        self.ids['search_input'] = MDTextField(
            hint_text="Buscar música...",
            mode="fill",
            fill_color_normal="#1A1A1A",
            fill_color_focus="#1A1A1A",
            hint_text_color_normal="#888888",
            hint_text_color_focus="#BB86FC",
            text_color_normal="#FFFFFF",
            text_color_focus="#FFFFFF",
            icon_left="magnify",
            icon_left_color_normal="#BB86FC",
            active_line_color_normal="#BB86FC"
        )
        self.ids['search_input'].bind(on_text_validate=lambda x: MDApp.get_running_app().search_songs(x.text))
        search_layout.add_widget(self.ids['search_input'])
        main_layout.add_widget(search_layout)
        
        header_layout = MDBoxLayout(size_hint_y=None, height=dp(40), padding=[dp(16), dp(8), dp(16), 0])
        self.ids['list_header'] = MDLabel(
            text="RECOMENDADOS",
            theme_text_color="Custom",
            text_color="#BB86FC",
            font_style="Subtitle2",
            bold=True,
            halign="left",
            valign="center"
        )
        header_layout.add_widget(self.ids['list_header'])
        main_layout.add_widget(header_layout)
        
        results_layout = MDBoxLayout(orientation="vertical", size_hint_y=1, padding=[dp(8), dp(4), dp(8), 0])
        self.ids['results_rv'] = RecycleView(
            size_hint=(1, 1),
            bar_width=dp(4),
            bar_color=[0.737, 0.525, 0.988, 0.5],
            bar_inactive_color=[0.737, 0.525, 0.988, 0.2],
            scroll_type=['bars', 'content']
        )
        self.ids['results_rv'].viewclass = 'SearchItem'
        
        self.rv_layout = RecycleBoxLayout(
            default_size=(None, dp(72)),
            default_size_hint=(1, None),
            size_hint_y=None,
            orientation='vertical',
            spacing=dp(8),
            padding=[dp(8), 0, dp(8), dp(8)]
        )
        self.rv_layout.bind(minimum_height=self.rv_layout.setter('height'))
        self.ids['results_rv'].add_widget(self.rv_layout)
        results_layout.add_widget(self.ids['results_rv'])
        main_layout.add_widget(results_layout)
        
        # Overlay for spinner
        self.ids['spinner_container'] = MDAnchorLayout(
            size_hint=(None, None),
            size=(dp(50), dp(50)),
            pos_hint={'center_x': 0.5, 'center_y': 0.5}
        )
        self.ids['search_spinner'] = MDSpinner(
            size_hint=(None, None),
            size=(dp(40), dp(40)),
            active=False,
            color="#BB86FC"
        )
        self.ids['spinner_container'].add_widget(self.ids['search_spinner'])
        
        # Root for screen
        root_rel = RelativeLayout()
        root_rel.add_widget(main_layout)
        root_rel.add_widget(self.ids['spinner_container'])
        
        fab = MDFloatingActionButton(
            icon="music-note",
            md_bg_color="#BB86FC",
            text_color="#000000",
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={"right": 0.95, "y": 0.02}
        )
        fab.bind(on_release=lambda x: MDApp.get_running_app().go_to_player())
        root_rel.add_widget(fab)
        
        self.add_widget(root_rel)

Factory.register('MobileScreenLibrary', cls=MobileScreenLibrary)

class MobileScreenOffline(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "offline"
        self.md_bg_color = "#000000"
        
        layout = MDBoxLayout(orientation="vertical")
        
        self.ids['top_bar'] = MDTopAppBar(
            title="Descargas",
            anchor_title="left",
            elevation=0,
            md_bg_color="#000000",
            specific_text_color="#FFFFFF",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().go_to_library()]],
            right_action_items=[["folder-settings", lambda x: MDApp.get_running_app().open_file_manager()]]
        )
        layout.add_widget(self.ids['top_bar'])
        
        content = MDBoxLayout(orientation="vertical", padding=[dp(8), dp(8), dp(8), dp(80)])
        self.ids['offline_rv'] = RecycleView(viewclass='OfflineItem')
        rv_layout = RecycleBoxLayout(
            default_size=(None, dp(72)),
            default_size_hint=(1, None),
            size_hint_y=None,
            orientation='vertical',
            spacing=dp(8),
            padding=[dp(8), 0, dp(8), 0]
        )
        rv_layout.bind(minimum_height=rv_layout.setter('height'))
        self.ids['offline_rv'].add_widget(rv_layout)
        content.add_widget(self.ids['offline_rv'])
        layout.add_widget(content)
        
        rel = RelativeLayout()
        rel.add_widget(layout)
        
        fab = MDFloatingActionButton(
            icon="refresh",
            md_bg_color="#BB86FC",
            text_color="#000000",
            size_hint=(None, None),
            size=(dp(56), dp(56)),
            pos_hint={"right": 0.95, "y": 0.02}
        )
        fab.bind(on_release=lambda x: MDApp.get_running_app().load_offline_songs())
        rel.add_widget(fab)
        
        self.add_widget(rel)

Factory.register('MobileScreenOffline', cls=MobileScreenOffline)

class MobileScreenPlaylists(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "playlists"
        self.md_bg_color = "#000000"
        
        layout = MDBoxLayout(orientation="vertical")
        
        self.ids['top_bar'] = MDTopAppBar(
            title="Mis Playlists",
            anchor_title="left",
            elevation=0,
            md_bg_color="#000000",
            specific_text_color="#FFFFFF",
            left_action_items=[["arrow-left", lambda x: MDApp.get_running_app().go_to_library()]],
            right_action_items=[["plus", lambda x: MDApp.get_running_app().create_playlist_dialog()]]
        )
        layout.add_widget(self.ids['top_bar'])
        
        content = MDBoxLayout(orientation="vertical", padding=[dp(8), dp(8), dp(8), dp(8)])
        self.ids['playlists_rv'] = RecycleView(viewclass='PlaylistItem')
        rv_layout = RecycleBoxLayout(
            default_size=(None, dp(72)),
            default_size_hint=(1, None),
            size_hint_y=None,
            orientation='vertical',
            spacing=dp(8),
            padding=[dp(8), 0, dp(8), 0]
        )
        rv_layout.bind(minimum_height=rv_layout.setter('height'))
        self.ids['playlists_rv'].add_widget(rv_layout)
        content.add_widget(self.ids['playlists_rv'])
        layout.add_widget(content)
        
        self.add_widget(layout)

Factory.register('MobileScreenPlaylists', cls=MobileScreenPlaylists)

class MobileScreenPlayer(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "player"
        self.md_bg_color = "#000000"
        
        layout = MDBoxLayout(orientation="vertical", spacing=dp(8))
        
        self.ids['top_bar'] = MDTopAppBar(
            title="",
            elevation=0,
            md_bg_color="#000000",
            specific_text_color="#BB86FC",
            left_action_items=[["chevron-down", lambda x: MDApp.get_running_app().go_to_library()]]
        )
        self.ids['top_bar'].right_action_items = [
            ["playlist-plus", lambda x: MDApp.get_running_app().add_song_to_playlist_dialog(MDApp.get_running_app().get_current_song_data())],
            ["download", lambda x: MDApp.get_running_app().download_song()]
        ]
        layout.add_widget(self.ids['top_bar'])
        
        # Album Art
        art_layout = MDBoxLayout(orientation="vertical", size_hint_y=0.42, padding=[dp(32), dp(16)])
        self.ids['album_card'] = MDCard(
            size_hint=(1, 1),
            radius=[dp(24)],
            elevation=8,
            md_bg_color="#000000",
            shadow_color=[0.737, 0.525, 0.988, 0.4]
        )
        with self.ids['album_card'].canvas.before:
            self.album_border_color = Color(0.737, 0.525, 0.988, 0.6)
            self.album_border = Line(width=3, rounded_rectangle=(0, 0, 0, 0, 24))
        self.ids['album_card'].bind(pos=self._update_album_border, size=self._update_album_border)
        
        self.ids['thumbnail'] = FitImage(radius=[dp(24)], allow_stretch=True, keep_ratio=False)
        self.ids['album_card'].add_widget(self.ids['thumbnail'])
        
        art_rel = RelativeLayout()
        art_rel.add_widget(self.ids['album_card'])
        
        self.ids['loading_spinner'] = MDSpinner(
            size_hint=(None, None),
            size=(dp(46), dp(46)),
            pos_hint={'center_x': .5, 'center_y': .5},
            active=False,
            color="#BB86FC"
        )
        art_rel.add_widget(self.ids['loading_spinner'])
        art_layout.add_widget(art_rel)
        layout.add_widget(art_layout)
        
        # Song Info
        info_layout = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(6), padding=[dp(24), dp(8)])
        self.ids['song_title'] = MDLabel(
            text="Título de la canción",
            halign="center",
            theme_text_color="Custom",
            text_color="#FFFFFF",
            font_size="20sp",
            bold=True,
            adaptive_height=True
        )
        self.ids['artist_name'] = MDLabel(
            text="Artista",
            halign="center",
            theme_text_color="Custom",
            text_color="#BB86FC",
            font_size="16sp",
            adaptive_height=True
        )
        info_layout.add_widget(self.ids['song_title'])
        info_layout.add_widget(self.ids['artist_name'])
        layout.add_widget(info_layout)
        
        # Progress Bar
        progress_layout = MDBoxLayout(orientation="vertical", adaptive_height=True, spacing=dp(8), padding=[dp(24), dp(12)])
        self.ids['progress_slider'] = MDSlider(
            size_hint_y=None, height=dp(30),
            min=0, max=100, value=0,
            color="#BB86FC", hint=False
        )
        progress_layout.add_widget(self.ids['progress_slider'])
        
        times_layout = MDBoxLayout(orientation="horizontal", adaptive_height=True)
        self.ids['current_time_label'] = MDLabel(
            text="00:00", font_size="12sp",
            theme_text_color="Custom", text_color="#888888",
            size_hint_x=1, halign="left"
        )
        self.ids['total_time_label'] = MDLabel(
            text="00:00", font_size="12sp",
            theme_text_color="Custom", text_color="#888888",
            size_hint_x=1, halign="right"
        )
        times_layout.add_widget(self.ids['current_time_label'])
        times_layout.add_widget(self.ids['total_time_label'])
        progress_layout.add_widget(times_layout)
        layout.add_widget(progress_layout)
        
        # Controls
        controls_layout = MDBoxLayout(orientation="vertical", size_hint_y=None, height=dp(220), padding=[0, dp(10), 0, dp(20)], spacing=dp(12))
        
        main_ctrl_anchor = MDAnchorLayout(anchor_x="center", anchor_y="center", size_hint_y=None, height=dp(64))
        main_ctrl_box = MDBoxLayout(orientation="horizontal", size_hint=(None, None), size=(dp(320), dp(48)), spacing=dp(16))
        
        rewind_btn = MDIconButton(icon="rewind-10", user_font_size="24sp", theme_text_color="Custom", text_color="#888888", size_hint=(None, None), size=(dp(48), dp(48)))
        rewind_btn.bind(on_release=lambda x: MDApp.get_running_app().seek_relative(-10))
        
        prev_btn = MDIconButton(icon="skip-previous", user_font_size="36sp", theme_text_color="Custom", text_color="#BB86FC", size_hint=(None, None), size=(dp(48), dp(48)))
        prev_btn.bind(on_release=lambda x: MDApp.get_running_app().on_previous())
        
        play_card = MDCard(size_hint=(None, None), size=(dp(56), dp(56)), radius=[dp(28)], elevation=4, md_bg_color="#BB86FC", shadow_color=[0.737, 0.525, 0.988, 0.6], pos_hint={"center_y": 0.5})
        self.ids['play_pause_btn'] = MDIconButton(icon="pause", user_font_size="32sp", theme_text_color="Custom", text_color="#000000", pos_hint={"center_x": .5, "center_y": .5}, size_hint=(1, 1))
        self.ids['play_pause_btn'].bind(on_release=lambda x: MDApp.get_running_app().toggle_playback())
        play_card.add_widget(self.ids['play_pause_btn'])
        
        next_btn = MDIconButton(icon="skip-next", user_font_size="36sp", theme_text_color="Custom", text_color="#BB86FC", size_hint=(None, None), size=(dp(48), dp(48)))
        next_btn.bind(on_release=lambda x: MDApp.get_running_app().on_next())
        
        ff_btn = MDIconButton(icon="fast-forward-10", user_font_size="24sp", theme_text_color="Custom", text_color="#888888", size_hint=(None, None), size=(dp(48), dp(48)))
        ff_btn.bind(on_release=lambda x: MDApp.get_running_app().seek_relative(10))
        
        main_ctrl_box.add_widget(rewind_btn)
        main_ctrl_box.add_widget(prev_btn)
        main_ctrl_box.add_widget(play_card)
        main_ctrl_box.add_widget(next_btn)
        main_ctrl_box.add_widget(ff_btn)
        main_ctrl_anchor.add_widget(main_ctrl_box)
        controls_layout.add_widget(main_ctrl_anchor)
        
        sec_ctrl_anchor = MDAnchorLayout(anchor_x="center", anchor_y="center", size_hint_y=None, height=dp(44))
        sec_ctrl_box = MDBoxLayout(orientation="horizontal", size_hint=(None, None), size=(dp(168), dp(40)), spacing=dp(24))
        
        self.ids['shuffle_btn'] = MDIconButton(icon="shuffle", user_font_size="18sp", theme_text_color="Custom", text_color="#444444", size_hint=(None, None), size=(dp(40), dp(40)))
        self.ids['shuffle_btn'].bind(on_release=lambda x: MDApp.get_running_app().toggle_shuffle())
        
        self.ids['repeat_btn'] = MDIconButton(icon="repeat", user_font_size="18sp", theme_text_color="Custom", text_color="#444444", size_hint=(None, None), size=(dp(40), dp(40)))
        self.ids['repeat_btn'].bind(on_release=lambda x: MDApp.get_running_app().toggle_repeat())
        
        self.ids['download_btn'] = MDIconButton(icon="download", user_font_size="18sp", theme_text_color="Custom", text_color="#BB86FC", size_hint=(None, None), size=(dp(40), dp(40)))
        self.ids['download_btn'].bind(on_release=lambda x: MDApp.get_running_app().download_song())
        
        sec_ctrl_box.add_widget(self.ids['shuffle_btn'])
        sec_ctrl_box.add_widget(self.ids['repeat_btn'])
        sec_ctrl_box.add_widget(self.ids['download_btn'])
        sec_ctrl_anchor.add_widget(sec_ctrl_box)
        controls_layout.add_widget(sec_ctrl_anchor)
        
        layout.add_widget(controls_layout)
        self.add_widget(layout)

    def _update_album_border(self, instance, value):
        self.album_border.rounded_rectangle = (instance.x, instance.y, instance.width, instance.height, 24)

Factory.register('MobileScreenPlayer', cls=MobileScreenPlayer)

class MobileRootLayout(MDScreenManager):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.add_widget(MobileScreenLibrary())
        self.add_widget(MobileScreenPlayer())
        self.add_widget(MobileScreenOffline())
        self.add_widget(MobileScreenPlaylists())

# Register classes in Factory
Factory.register('ModernCard', cls=ModernCard)
Factory.register('GlowingIconButton', cls=GlowingIconButton)
Factory.register('SectionTitle', cls=SectionTitle)
Factory.register('SubsectionTitle', cls=SubsectionTitle)
Factory.register('MoodChip', cls=MoodChip)
Factory.register('ModernSongCard', cls=ModernSongCard)
Factory.register('SearchItem', cls=SearchItem)
Factory.register('PlaylistItem', cls=PlaylistItem)
Factory.register('OfflineItem', cls=OfflineItem)
Factory.register('MobileScreenLibrary', cls=MobileScreenLibrary)
Factory.register('MobileScreenOffline', cls=MobileScreenOffline)
Factory.register('MobileScreenPlaylists', cls=MobileScreenPlaylists)
Factory.register('MobileScreenPlayer', cls=MobileScreenPlayer)
Factory.register('MobileRootLayout', cls=MobileRootLayout)


class MusicPlayerApp(MDApp):
    is_shuffle = BooleanProperty(False)
    is_repeat = BooleanProperty(False)
    is_seeking = BooleanProperty(False)
    album_scale = NumericProperty(1.0)
    title_glow = NumericProperty(1.0)
    # Track what is currently being shown on the library screen
    # Modes: 'recommendations', 'search', 'playlist', 'offline'
    library_mode = StringProperty('recommendations')
    current_screen = StringProperty('library')

    @property
    def root_sm(self):
        """Cross-platform ScreenManager access with safety checks"""
        if not self.root:
            return None
        try:
            if platform != "android" and hasattr(self.root, 'ids') and 'screen_manager' in self.root.ids:
                return self.root.ids['screen_manager']
        except: pass
        return self.root

    def change_theme(self, color_hex):
        """Dynamic theme color switching for personalization"""
        # Convert hex to KivyMD palette name if possible, or just set it
        # For simplicity, we can use predefined palettes or just update the theme_cls
        self.theme_cls.primary_palette = "DeepPurple" if color_hex == "#BB86FC" else \
                                        "Green" if color_hex == "#00E676" else \
                                        "Blue" if color_hex == "#2979FF" else \
                                        "Red" if color_hex == "#FF5252" else "DeepPurple"
        toast(f"Tema actualizado")

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
        self.is_local_playback = False  # Track if current playback is local or online
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
            safe_path = os.path.join(self.user_data_dir, 'playlists.json')
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
            save_dir = self.user_data_dir
            os.makedirs(save_dir, exist_ok=True)
            path = os.path.join(save_dir, 'playlists.json')
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(self.playlists, f, indent=4)
            Logger.info(f"App: Playlists saved to {path}")
        except Exception as e:
            Logger.error(f"App: Failed to save playlists: {e}")
            Clock.schedule_once(lambda dt: toast("Error al guardar"))

    def go_to_playlists(self):
        self.root_sm.transition = SlideTransition(direction="left")
        self.root_sm.current = "playlists"
        self.display_playlists()

    def go_to_offline(self):
        self.root_sm.transition = SlideTransition(direction="right")
        self.root_sm.current = "offline"
        self.load_offline_songs()

    def _on_screen_change(self, instance, value):
        self.current_screen = value

    def build(self):
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

        # Load appropriate UI based on platform
        try:
            if platform == "android":
                self.root = MobileRootLayout()
            else:
                self.root = get_desktop_ui()
        except Exception as e:
            import traceback
            error_trace = traceback.format_exc()
            Logger.error(f"App: Error crítico cargando UI:\n{error_trace}")
            from kivymd.uix.label import MDLabel
            return MDLabel(text=f"Error al iniciar:\n{str(e)[:100]}", halign="center")
        
        root = self.root
        
        # Bind screen manager change
        sm = root.ids['screen_manager'] if platform != "android" else root
        sm.bind(current=self._on_screen_change)
        
        # Bind Slider & Back Button
        # Use root_sm to find the player screen
        player_screen = root.ids['screen_manager'].get_screen("player") if platform != "android" else root.get_screen("player")
        slider = player_screen.ids['progress_slider']
        slider.bind(on_touch_down=self._slider_touch_down)
        slider.bind(on_touch_up=self._slider_touch_up)
        
        # If desktop, also bind the bottom bar slider
        if platform != "android":
            bottom_slider = root.ids['bottom_progress']
            bottom_slider.bind(on_touch_down=self._slider_touch_down)
            bottom_slider.bind(on_touch_up=self._slider_touch_up)
        
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
            current = self.root_sm.current
            screen_back_map = {
                'player':    'library',
                'playlists': 'library',
                'offline':   'library',
            }
            if current in screen_back_map:
                self.root_sm.transition = SlideTransition(direction='right')
                self.root_sm.current = screen_back_map[current]
                return True
            
            # Priority 4: On the main screen — handle playlist view / search or exit
            if current == 'library':
                # 1. Check if we are viewing a playlist or search results
                if self.library_mode != 'recommendations':
                    self.library_mode = 'recommendations'
                    # NUEVO: Ocultar flecha de regreso
                    self.update_top_bar(show_back=False)
                    # Restore cached recommendations instantly if they exist
                    if self.recommendations_cache:
                        self._update_results_rv(self.recommendations_cache, "RECOMENDADOS PARA TI")
                    else:
                        # Fallback: re-fetch if cache is empty
                        threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
                    
                    # Also clear search input for clean UI
                    try:
                        self.root_sm.get_screen("library").ids['search_input'].text = ""
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
        # 1. Initialize Paths & Storage
        self._init_music_path()
        
        # 2. Initialize player here to ensure Android Activity is ready
        if not self.player:
            from player import get_best_player
            self.player = get_best_player()
            Logger.info("App: Audio engine initialized in on_start")

        if platform == "android":
             # 3. Request permissions & Start Service
            self._setup_media_receiver()
            self._request_android_permissions()
        
        # 4. Load recommendations in background thread
        threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()

    def _request_android_permissions(self):
        """Dynamic permission request for Android 14 (API 34)"""
        try:
            from android.permissions import request_permissions, Permission, check_permission # type: ignore
            from android import api_version # type: ignore
            
            perms = [Permission.INTERNET, Permission.WAKE_LOCK]
            if api_version >= 33:
                perms.append("android.permission.POST_NOTIFICATIONS")
            if api_version >= 33:
                # Android 13+ granular permissions
                perms.append(Permission.READ_MEDIA_AUDIO)
            else:
                perms.append(Permission.READ_EXTERNAL_STORAGE)
                perms.append(Permission.WRITE_EXTERNAL_STORAGE)
            
            # Check for All Files Access (MANAGE_EXTERNAL_STORAGE)
            if api_version >= 30:
                try:
                    # Usually requires intent to settings, but declaring it helps
                    # perms.append("android.permission.MANAGE_EXTERNAL_STORAGE")
                    pass
                except: pass

            # Check if all permissions are already granted
            all_granted = True
            for p in perms:
                if not check_permission(p):
                    all_granted = False
                    break
            
            if all_granted:
                Logger.info("App: All permissions already granted, starting service directly")
                self._on_permissions_callback(perms, [True]*len(perms))
            else:
                Logger.info(f"App: Requesting permissions: {perms}")
                request_permissions(perms, self._on_permissions_callback)
        except Exception as e:
            Logger.error(f"App: Permissions error: {e}")

    def _on_permissions_callback(self, permissions, grants):
        """Callback for permission result"""
        for p, g in zip(permissions, grants):
            if not g:
                Logger.warning(f"App: Permission {p} denied")
        
        # Start playback service AFTER permissions have been requested/granted
        self._start_playback_service()
        
        # If API 30+, check if we need to ask for MANAGE_EXTERNAL_STORAGE manually
        if platform == "android":
            from android import api_version # type: ignore
            if api_version >= 30:
                self._check_manage_storage_permission()

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
        """Start the background service using p4a's AndroidService API (correct method).
        
        DIAGNOSIS: The previous autoclass('ServicePlayback').start() call silently failed
        because ServicePlayback is a wrapper class generated by p4a — it must be started
        through the p4a AndroidService bridge, NOT directly via autoclass.
        """
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
                    intent.setClassName(mActivity, service_name)
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
        """Fallback: build the MediaStyle notification directly from the Activity context.
        This is less ideal than a Service (the OS can kill it when app is minimized)
        but guarantees the notification shows while the app is in the foreground.
        """
        try:
            from jnius import autoclass  # type: ignore
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

            def make_pi(action, code):
                i = Intent(action)
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
            ms = MediaSession(mActivity, 'KivyActivitySession')
            ms.setActive(True)
            self._media_session_act = ms  # Keep global reference

            # FIX: Set PlaybackState (MANDATORY for Android 13+ lockscreen)
            PlaybackStateBuilder = autoclass('android.media.session.PlaybackState$Builder')
            psb = PlaybackStateBuilder()
            # Actions: PLAY, PAUSE, SKIP_TO_NEXT, SKIP_TO_PREVIOUS (mask: 0b110110 = 54)
            psb.setActions(54) 
            psb.setState(3, 0, 1.0) # STATE_PLAYING = 3
            ms.setPlaybackState(psb.build())

            style = MediaStyle()
            style.setMediaSession(ms.getSessionToken())
            style.setShowActionsInCompactView(0, 1, 2)

            String = autoclass('java.lang.String')
            b = NotificationBuilder(mActivity, String(channel_id)) if api_version >= 26 else NotificationBuilder(mActivity)
            b.setContentTitle(String('Reproductor Activo'))
            b.setContentText(String('Escuchando música...'))
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

    def update_activity_notification(self, title, artist, state='playing'):
        """Update the fallback notification (built from Activity) with current song info."""
        try:
            if not hasattr(self, '_notif_nm') or not self._notif_nm:
                return
            from jnius import autoclass  # type: ignore
            from android import api_version  # type: ignore

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
            String = autoclass('java.lang.String')
            
            b = NotificationBuilder(mActivity, ch) if api_version >= 26 else NotificationBuilder(mActivity)
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
                ps_builder.setActions(54)
                # Cast strings to CharSequence to avoid Jnius constructor matching issues
                String = autoclass('java.lang.String')
                
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
                ps_builder.setState(state_int, 0, 1.0)
                self._media_session_act.setPlaybackState(ps_builder.build())

                # Update Metadata
                MediaMetadataBuilder = autoclass('android.media.MediaMetadata$Builder')
                meta = MediaMetadataBuilder()
                meta.putString('android.media.metadata.TITLE',  title)
                meta.putString('android.media.metadata.ARTIST', artist)
                self._media_session_act.setMetadata(meta.build())
            except Exception: pass
        except Exception as e:
            Logger.warning(f"App: update_activity_notification failed: {e}")

    def _setup_media_receiver(self):
        """Sets up a BroadcastReceiver to listen to lockscreen button intents from service.py"""
        try:
            from jnius import autoclass, PythonJavaClass, java_method # type: ignore
            from android import api_version # type: ignore
            
            class MediaActionReceiver(PythonJavaClass):
                __javainterfaces__ = ['android/content/BroadcastReceiver']
                __javacontext__ = 'app'
                
                def __init__(self, app_instance):
                    super().__init__()
                    self.app = app_instance
                    
                @java_method('(Landroid/content/Context;Landroid/content/Intent;)V')
                def onReceive(self, context, intent):
                    try:
                        action = intent.getAction()
                        if action == "org.test.musicplayeryt.ACTION_PLAY":
                            if not self.app.player.is_playing():
                                self.app.toggle_playback()
                        elif action == "org.test.musicplayeryt.ACTION_PAUSE":
                            if self.app.player.is_playing():
                                self.app.toggle_playback()
                        elif action == "org.test.musicplayeryt.ACTION_NEXT":
                            self.app.on_next()
                        elif action == "org.test.musicplayeryt.ACTION_PREV":
                            self.app.on_previous()
                    except Exception as e:
                        Logger.error(f"App: MediaActionReceiver Error: {e}")

            self._media_receiver = MediaActionReceiver(self)
            IntentFilter = autoclass('android.content.IntentFilter')
            filter = IntentFilter()
            filter.addAction("org.test.musicplayeryt.ACTION_PLAY")
            filter.addAction("org.test.musicplayeryt.ACTION_PAUSE")
            filter.addAction("org.test.musicplayeryt.ACTION_NEXT")
            filter.addAction("org.test.musicplayeryt.ACTION_PREV")
            
            PythonActivity = autoclass('org.kivy.android.PythonActivity')
            mActivity = PythonActivity.mActivity
            
            if api_version >= 33:
                mActivity.registerReceiver(self._media_receiver, filter, 2) # RECEIVER_EXPORTED
            else:
                mActivity.registerReceiver(self._media_receiver, filter)
            
            Logger.info("App: MediaActionReceiver successfully registered")
        except Exception as e:
            Logger.error(f"App: Failed to setup media receiver: {e}")

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
        self.root_sm.transition = SlideTransition(direction="right")
        self.root_sm.current = "library"

    def go_to_offline(self):
        self.root_sm.transition = SlideTransition(direction="left")
        self.root_sm.current = "offline"
        self.load_offline_songs()

    def go_to_player(self):
        if self.current_index != -1:
            self.root_sm.transition = SlideTransition(direction="up")
            self.root_sm.current = "player"
        else:
            toast("Nada en reproducción")

    def toggle_shuffle(self):
        self.is_shuffle = not self.is_shuffle
        btn = self.root_sm.get_screen("player").ids.shuffle_btn
        btn.text_color = "#BB86FC" if self.is_shuffle else "#444444"
        toast("Aleatorio: ON" if self.is_shuffle else "Aleatorio: OFF")

    def toggle_repeat(self):
        self.is_repeat = not self.is_repeat
        btn = self.root_sm.get_screen("player").ids.repeat_btn
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
        
        # NUEVO: Mostrar flecha de regreso en búsqueda
        self.update_top_bar(show_back=True, title=f"Buscar: {query}")
        
        # UI State - Instant feedback
        self.root_sm.get_screen("library").ids.search_spinner.active = True
        
        if query not in self.search_history:
            self.search_history.insert(0, query)
            self.search_history = self.search_history[:5]
            
        # Concurrency: Use threading to avoid blocking main loop
        threading.Thread(target=self._search_songs_thread, args=(query,), daemon=True).start()

    def _get_best_thumb(self, thumbnails):
        """Helper to extract the highest resolution thumbnail available"""
        if not thumbnails: return ""
        if isinstance(thumbnails, str): return thumbnails
        try:
            # Sort by width/height descending
            valid_thumbs = [t for t in thumbnails if t.get('url')]
            if not valid_thumbs: return ""
            valid_thumbs.sort(key=lambda x: x.get('width', 0) or x.get('height', 0), reverse=True)
            return valid_thumbs[0]['url']
        except Exception:
            try: return thumbnails[0]['url']
            except: return ""

    @mainthread
    def _update_results_rv(self, results, title):
        """Thread-safe UI update using RecycleView.data"""
        lib_ids = self.root_sm.get_screen("library").ids
        lib_ids['search_spinner'].active = False
        lib_ids['list_header'].text = title
        
        self.last_results = results
        
        # Map raw results to SearchItem properties
        rv_data = []
        for i, res in enumerate(results):
            best_thumb = self._get_best_thumb(res.get('thumbnails', [])) or res.get('thumbnail', '')
            rv_data.append({
                'title': str(res.get('title', 'Unknown')),
                'artist': res.get('artist', 'YouTube'),
                'thumbnail': best_thumb,
                'index': i,
                'song_data': res,
                'is_playlist_view': False
            })
        
        lib_ids['results_rv'].data = rv_data
        
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
        offline_rv = self.root_sm.get_screen("offline").ids['offline_rv']
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
        self.is_local_playback = True  # Mark as local playback
        
        # Switch to player screen immediately
        self.root_sm.transition = SlideTransition(direction="up")
        self.root_sm.current = "player"
        
        # Validate path
        path = data['url']
        if not path or not os.path.exists(path):
            Logger.error(f"App: Local file not found: {path}")
            self._on_playback_error("Archivo local no encontrado")
            return

        # Prepare UI
        player_screen = self.root_sm.get_screen("player")
        player_screen.ids['song_title'].text = data['title']
        player_screen.ids['artist_name'].text = "Local"
        player_screen.ids['play_pause_btn'].icon = "pause-circle"
        player_screen.ids['loading_spinner'].active = True # Show loading while opening file

        # Update Desktop Bottom Bar
        if platform != "android":
            try:
                self.root.ids['bottom_title'].text = data.get('title', 'Cargando...')
                self.root.ids['bottom_artist'].text = "Local"
                self.root.ids['side_player_title'].text = data.get('title', 'Cargando...')
                self.root.ids['bottom_thumb'].source = "music-note"
                self.root.ids['side_player_thumb'].source = "music-note"
            except Exception as e:
                Logger.debug(f"App: Bottom bar play local update error: {e}")

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
        self.is_local_playback = False  # Mark as online playback
        data = self.current_playlist[self.current_index]
        
        # Show Loading on Player Screen
        self.root_sm.transition = SlideTransition(direction="up")
        self.root_sm.current = "player"
        player_screen = self.root_sm.get_screen("player")
        player_screen.ids.loading_spinner.active = True
        player_screen.ids.song_title.text = "Cargando..."
        player_screen.ids.artist_name.text = data.get('artist', 'YouTube')

        # Update Desktop Bottom Bar
        if platform != "android":
            try:
                self.root.ids.bottom_title.text = data.get('title', 'Cargando...')
                self.root.ids.bottom_artist.text = data.get('artist', 'YouTube')
                self.root.ids.side_player_title.text = data.get('title', 'Cargando...')
                thumb = data.get('thumbnails', [{}])[0].get('url', '') if data.get('thumbnails') else ''
                if thumb:
                    self.root.ids.bottom_thumb.source = thumb
                    self.root.ids.side_player_thumb.source = thumb
            except Exception as e:
                Logger.debug(f"App: Bottom bar play update error: {e}")
        
        # Optimization: Use ThreadPoolExecutor
        self.executor.submit(self._prepare_playback_thread, data)

    @mainthread
    def display_playlists(self):
        playlists_rv = self.root_sm.get_screen("playlists").ids.playlists_rv
        rv_data = []
        
        for name in self.playlists.keys():
            rv_data.append({
                'text': name,
                'playlist_name': name
            })
        
        playlists_rv.data = rv_data

    def update_top_bar(self, show_back=False, title="Mi Biblioteca"):
        """Actualizar la barra superior para mostrar/ocultar flecha de regreso"""
        try:
            top_bar = self.root_sm.get_screen("library").ids.top_bar
            
            if show_back:
                # Mostrar flecha de regreso + título personalizado
                top_bar.title = title
                top_bar.left_action_items = [["arrow-left", lambda x: self.back_to_recommendations()]]
            else:
                # Ocultar flecha, mostrar título normal
                top_bar.title = "Mi Biblioteca"
                top_bar.left_action_items = []
                
        except Exception as e:
            Logger.error(f"App: Error actualizando top bar: {e}")

    def back_to_recommendations(self):
        """Función para regresar a recomendaciones cuando se presiona la flecha"""
        try:
            Logger.info("App: Regresando a recomendaciones vía botón de regreso")
            
            # Resetear modo a recommendations
            self.library_mode = 'recommendations'
            
            # Actualizar UI
            self.root_sm.get_screen("library").ids.list_header.text = "RECOMENDADOS PARA TI"
            
            # Actualizar top bar para ocultar flecha
            self.update_top_bar(show_back=False)
            
            # Limpiar búsqueda
            try:
                self.root_sm.get_screen("library").ids.search_input.text = ""
            except:
                pass
            
            # Cargar recommendations
            if self.recommendations_cache:
                self._update_results_rv(self.recommendations_cache, "RECOMENDADOS PARA TI")
            else:
                threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
                self.root_sm.get_screen("library").ids.list_header.text = "CARGANDO RECOMENDACIONES..."
            
        except Exception as e:
            Logger.error(f"App: Error en back_to_recommendations: {e}")

    def open_playlist(self, name):
        try:
            self.current_playlist_name = name
            self.library_mode = 'playlist'
            songs = self.playlists.get(name, [])
            if not isinstance(songs, list):
                Logger.error(f"App: Corrupt playlist data for {name}")
                songs = []
            
            # NUEVO: Mostrar flecha de regreso al abrir playlist
            self.update_top_bar(show_back=True, title=name)
            
            self.root_sm.transition = SlideTransition(direction="left")
            self.root_sm.current = "library"
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
            lib_ids = self.root_sm.get_screen("library").ids
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
        player_screen = self.root_sm.get_screen("player")
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
        player_screen = self.root_sm.get_screen("player")
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
            Clock.schedule_once(lambda dt: self._start_playback_delayed(url), 0.1)
        except Exception as e:
            Logger.error(f"App: Playback scheduling error: {e}")
            self._on_playback_error(f"Error al reproducir: {str(e)[:50]}")

    def _start_playback_delayed(self, url):
        """Metodo intermedio para asegurar que el thread se inicia correctamente"""
        self._do_playback(url)
    
    def _do_playback(self, url):
        """Ejecutar la reproducción en thread separado para no bloquear UI"""
        try:
            player_screen = self.root_sm.get_screen("player")
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
            
            player_screen = self.root_sm.get_screen("player")
            def update_icon(dt):
                player_screen.ids.play_pause_btn.icon = "pause-circle"
                if platform != "android":
                    try:
                        self.root.ids.bottom_play_btn.icon = "pause"
                    except: pass
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
            self.update_activity_notification(song.get('title', ''), song.get('artist', ''), 'playing')

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
        
        # Use appropriate playback method based on current mode
        if self.is_local_playback:
            self.play_local_song(self.current_index)
        else:
            self.play_selected_song(self.current_index)

    def on_previous(self):
        if not self.player: return
        if not self.current_playlist: return
        self.current_index = (self.current_index - 1) % len(self.current_playlist)
        
        # Use appropriate playback method based on current mode
        if self.is_local_playback:
            self.play_local_song(self.current_index)
        else:
            self.play_selected_song(self.current_index)

    def _update_ui(self, dt):
        if not self.player or self.is_seeking:
            return
        
        try:
            length = self.player.get_length() if self.player else 0
            current = self.player.get_time() if self.player else 0
            
            if length > 0:
                progress = (current / length) * 100
                player_screen = self.root_sm.get_screen("player")
                player_screen.ids.progress_slider.value = progress
                player_screen.ids.current_time_label.text = self._format_time(current)
                player_screen.ids.total_time_label.text = self._format_time(length)
                
                # Update Desktop Bottom Bar
                if platform != "android":
                    try:
                        self.root.ids.bottom_progress.value = progress
                        self.root.ids.bottom_current_time.text = self._format_time(current)
                        self.root.ids.bottom_total_time.text = self._format_time(length)
                    except: pass

                # Pre-fetch logic (85% through)
                if progress > 85 and self.current_playlist:
                    self._check_pre_fetch()
                
                if current >= length - 1500 and length > 5000:
                    if self.is_repeat:
                        self.player.set_time(0)
                        self.player.play()
                    else:
                        # Auto-advance for both online and local playback
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
        player_screen = self.root_sm.get_screen("player")
        if self.player.is_playing():
            self.player.pause()
            self.update_service_metadata("paused")
            player_screen.ids.play_pause_btn.icon = "play-circle"
            if platform != "android":
                try: self.root.ids.bottom_play_btn.icon = "play"
                except: pass
            if self.pulse_anim: self.pulse_anim.cancel(self)
            if self.current_index >= 0 and self.current_playlist:
                s = self.current_playlist[self.current_index]
                self.update_activity_notification(s.get('title', ''), s.get('artist', ''), 'paused')
        else:
            self.player.resume() 
            self.update_service_metadata("playing")
            player_screen.ids.play_pause_btn.icon = "pause-circle"
            if platform != "android":
                try: self.root.ids.bottom_play_btn.icon = "pause"
                except: pass
            if self.pulse_anim: self.pulse_anim.start(self)
            if self.current_index >= 0 and self.current_playlist:
                s = self.current_playlist[self.current_index]
                self.update_activity_notification(s.get('title', ''), s.get('artist', ''), 'playing')

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
            player_screen = self.root_sm.get_screen("player")
            player_screen.ids.current_time_label.text = self._format_time(target_ms)
            
            if platform != "android":
                try: self.root.ids.bottom_current_time.text = self._format_time(target_ms)
                except: pass

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
                player_screen = self.root_sm.get_screen("player")
                player_screen.ids.progress_slider.value = (new_time / length) * 100
                player_screen.ids.current_time_label.text = self._format_time(new_time)
                
                if platform != "android":
                    try:
                        self.root.ids.bottom_progress.value = (new_time / length) * 100
                        self.root.ids.bottom_current_time.text = self._format_time(new_time)
                    except: pass
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
    try:
        MusicPlayerApp().run()
    except Exception as e:
        import traceback
        error_msg = traceback.format_exc()
        print(error_msg)
        with open("error_report.txt", "w") as f:
            f.write(error_msg)
