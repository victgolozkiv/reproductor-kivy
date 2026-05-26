from kivy.metrics import dp
from kivy.properties import StringProperty, NumericProperty, BooleanProperty, ListProperty, ObjectProperty
from kivy.uix.recycleview import RecycleView
from kivy.uix.recyclegridlayout import RecycleGridLayout
from kivy.uix.recycleboxlayout import RecycleBoxLayout
from kivy.uix.relativelayout import RelativeLayout
from kivy.uix.widget import Widget
from kivy.graphics import Color, Line
from kivy.factory import Factory
from kivy.clock import Clock

from kivymd.app import MDApp
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDIconButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.screen import MDScreen
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.spinner import MDSpinner
from kivymd.uix.slider import MDSlider
from kivymd.uix.fitimage import FitImage
from kivymd.uix.gridlayout import MDGridLayout

class DesktopPlaylistItem(MDCard):
    text = StringProperty()
    playlist_name = StringProperty()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#121212"
        self.radius = [dp(12)]
        self.elevation = 2
        self.padding = [dp(12), dp(10)]
        self.ripple_behavior = True
        
        layout = MDBoxLayout(orientation="horizontal", spacing=dp(12))
        layout.add_widget(MDIcon(
            icon="playlist-music",
            theme_text_color="Custom",
            text_color="#BB86FC",
            font_size="32sp",
            pos_hint={"center_y": 0.5}
        ))
        self.label = MDLabel(
            theme_text_color="Custom",
            text_color="#FFFFFF",
            bold=True,
            pos_hint={"center_y": 0.5}
        )
        layout.add_widget(self.label)
        self.add_widget(layout)
        self.bind(text=self.update_label)

    def update_label(self, *args):
        self.label.text = self.text

    def on_release(self):
        MDApp.get_running_app().open_playlist(self.text)

class DesktopOfflineItem(MDCard):
    title = StringProperty()
    artist = StringProperty()
    index = NumericProperty()
    song_data = ObjectProperty()
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#121212"
        self.radius = [dp(12)]
        self.elevation = 2
        self.padding = [dp(12), dp(8)]
        self.ripple_behavior = True
        
        layout = MDBoxLayout(orientation="horizontal", spacing=dp(12))
        layout.add_widget(MDIcon(
            icon="music-note",
            theme_text_color="Custom",
            text_color="#BB86FC",
            font_size="32sp",
            pos_hint={"center_y": 0.5}
        ))
        
        labels_layout = MDBoxLayout(orientation="vertical")
        self.title_label = MDLabel(
            theme_text_color="Custom",
            text_color="#FFFFFF",
            bold=True
        )
        self.artist_label = MDLabel(
            theme_text_color="Secondary",
            font_style="Caption"
        )
        labels_layout.add_widget(self.title_label)
        labels_layout.add_widget(self.artist_label)
        layout.add_widget(labels_layout)
        self.add_widget(layout)
        self.bind(title=self.update_labels, artist=self.update_labels)

    def update_labels(self, *args):
        self.title_label.text = self.title
        self.artist_label.text = self.artist

    def on_release(self):
        MDApp.get_running_app().play_local_song(self.index)

class DesktopSidebarItem(MDCard):
    text = StringProperty()
    icon = StringProperty()
    active = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "horizontal"
        self.size_hint_y = None
        self.height = dp(50)
        self.radius = [dp(12)]
        self.padding = [dp(12), 0]
        self.spacing = dp(12)
        self.ripple_behavior = True
        
        self.icon_widget = MDIcon(
            pos_hint={"center_y": 0.5},
            font_size="24sp"
        )
        self.label = MDLabel(
            font_style="Button",
            pos_hint={"center_y": 0.5}
        )
        self.add_widget(self.icon_widget)
        self.add_widget(self.label)
        
        self.bind(active=self.update_style, text=self.update_content, icon=self.update_content)
        self.update_style()
        self.update_content()

    def update_style(self, *args):
        if self.active:
            self.md_bg_color = [1, 1, 1, 0.05]
            self.icon_widget.theme_text_color = "Custom"
            self.icon_widget.text_color = "#BB86FC"
            self.label.theme_text_color = "Custom"
            self.label.text_color = "#FFFFFF"
            self.label.bold = True
        else:
            self.md_bg_color = [0, 0, 0, 0]
            self.icon_widget.theme_text_color = "Custom"
            self.icon_widget.text_color = "#B3B3B3"
            self.label.theme_text_color = "Custom"
            self.label.text_color = "#B3B3B3"
            self.label.bold = False

    def update_content(self, *args):
        self.label.text = self.text
        self.icon_widget.icon = self.icon

class DesktopSearchItem(MDCard):
    title = StringProperty("Sin título")
    artist = StringProperty("YouTube Music")
    thumbnail = StringProperty("")
    index = NumericProperty(0)
    song_data = ObjectProperty()
    is_playlist_view = BooleanProperty(False)
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.md_bg_color = "#181818"
        self.radius = [dp(16)]
        self.elevation = 0
        self.padding = 0
        self.orientation = "vertical"
        self.ripple_behavior = True
        
        self.rel_layout = RelativeLayout(size_hint_y=None)
        self.rel_layout.bind(width=self._update_rel_height)
        
        self.card_thumbnail = FitImage(
            radius=[dp(16), dp(16), 0, 0]
        )
        self.rel_layout.add_widget(self.card_thumbnail)
        self.add_widget(self.rel_layout)
        
        info_layout = MDBoxLayout(
            orientation="vertical",
            padding=[dp(12), dp(16), dp(12), dp(16)],
            spacing=dp(4),
            adaptive_height=True
        )
        self.title_label = MDLabel(
            bold=True,
            font_style="H6",
            font_size="16sp",
            theme_text_color="Custom",
            text_color="#FFFFFF",
            shorten=True,
            shorten_from="right",
            adaptive_height=True
        )
        self.artist_label = MDLabel(
            theme_text_color="Custom",
            text_color="#B3B3B3",
            font_style="Caption",
            font_size="13sp",
            shorten=True,
            adaptive_height=True
        )
        info_layout.add_widget(self.title_label)
        info_layout.add_widget(self.artist_label)
        self.add_widget(info_layout)
        
        self.bind(title=self.update_content, artist=self.update_content, thumbnail=self.update_content)
        self.update_content()

    def _update_rel_height(self, instance, value):
        instance.height = value

    def update_content(self, *args):
        self.title_label.text = self.title
        self.artist_label.text = self.artist
        self.card_thumbnail.source = self.thumbnail

    def on_release(self):
        MDApp.get_running_app().play_selected_song(self.index)

class DesktopScreenLibrary(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "library"
        layout = MDBoxLayout(orientation="vertical", padding=[0, dp(20), 0, 0], spacing=dp(20))
        
        header_layout = MDBoxLayout(adaptive_height=True, spacing=dp(20))
        self.ids["list_header"] = MDLabel(
            text="Recomendados para ti",
            font_style="H5",
            bold=True
        )
        self.ids["search_spinner"] = MDSpinner(
            size_hint=(None, None),
            size=(dp(30), dp(30)),
            active=False,
            color="#BB86FC"
        )
        header_layout.add_widget(self.ids["list_header"])
        header_layout.add_widget(self.ids["search_spinner"])
        layout.add_widget(header_layout)
        
        self.ids["results_rv"] = RecycleView()
        self.ids["results_rv"].viewclass = 'DesktopSearchItem'
        
        grid = RecycleGridLayout(
            cols=4,
            default_size=(None, dp(240)),
            default_size_hint=(1, None),
            size_hint_y=None,
            spacing=dp(20),
            padding=[0, 0, dp(20), dp(20)]
        )
        grid.bind(minimum_height=grid.setter('height'))
        self.ids["results_rv"].add_widget(grid)
        layout.add_widget(self.ids["results_rv"])
        self.add_widget(layout)

class DesktopScreenPlaylists(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "playlists"
        layout = MDBoxLayout(orientation="vertical", padding=[0, dp(20), 0, 0], spacing=dp(20))
        layout.add_widget(MDLabel(text="Mis Playlists", font_style="H5", bold=True))
        
        self.ids["playlists_rv"] = RecycleView()
        self.ids["playlists_rv"].viewclass = 'DesktopPlaylistItem'
        grid = RecycleGridLayout(
            cols=3,
            default_size=(None, dp(80)),
            default_size_hint=(1, None),
            size_hint_y=None,
            spacing=dp(16)
        )
        grid.bind(minimum_height=grid.setter('height'))
        self.ids["playlists_rv"].add_widget(grid)
        layout.add_widget(self.ids["playlists_rv"])
        self.add_widget(layout)

class DesktopScreenOffline(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "offline"
        layout = MDBoxLayout(orientation="vertical", padding=[0, dp(20), 0, 0], spacing=dp(20))
        layout.add_widget(MDLabel(text="Música Descargada", font_style="H5", bold=True))
        
        self.ids["offline_rv"] = RecycleView()
        self.ids["offline_rv"].viewclass = 'DesktopOfflineItem'
        box = RecycleBoxLayout(
            default_size=(None, dp(80)),
            default_size_hint=(1, None),
            size_hint_y=None,
            orientation='vertical',
            spacing=dp(8)
        )
        box.bind(minimum_height=box.setter('height'))
        self.ids["offline_rv"].add_widget(box)
        layout.add_widget(self.ids["offline_rv"])
        self.add_widget(layout)

class DesktopScreenPlayer(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.name = "player"
        layout = MDBoxLayout(orientation="horizontal", padding=dp(40), spacing=dp(60))
        
        # Big Album Art
        card = MDCard(
            size_hint=(None, None),
            size=(dp(450), dp(450)),
            radius=[dp(24)],
            elevation=8,
            pos_hint={"center_y": 0.5}
        )
        self.ids["thumbnail"] = FitImage(radius=[dp(24)])
        card.add_widget(self.ids["thumbnail"])
        layout.add_widget(card)
        
        # Info & Lyrics
        info_layout = MDBoxLayout(orientation="vertical", spacing=dp(24), pos_hint={"center_y": 0.5})
        
        self.ids["song_title"] = MDLabel(
            text="Título de la canción",
            font_style="H3",
            bold=True,
            adaptive_height=True
        )
        self.ids["artist_name"] = MDLabel(
            text="Nombre del Artista",
            font_style="H5",
            theme_text_color="Secondary",
            adaptive_height=True
        )
        info_layout.add_widget(self.ids["song_title"])
        info_layout.add_widget(self.ids["artist_name"])
        
        actions_layout = MDBoxLayout(adaptive_height=True, spacing=dp(16))
        actions_layout.add_widget(MDIconButton(icon="heart-outline", user_font_size="32sp"))
        actions_layout.add_widget(MDIconButton(icon="playlist-plus", user_font_size="32sp"))
        info_layout.add_widget(actions_layout)
        
        self.ids["loading_spinner"] = MDSpinner(
            active=False,
            size_hint=(None, None),
            size=(dp(48), dp(48))
        )
        info_layout.add_widget(self.ids["loading_spinner"])
        
        # Hidden compatibility widgets
        self.ids["progress_slider"] = MDSlider(opacity=0, size_hint_y=None, height=0)
        self.ids["current_time_label"] = MDLabel(opacity=0, height=0)
        self.ids["total_time_label"] = MDLabel(opacity=0, height=0)
        self.ids["play_pause_btn"] = MDIconButton(opacity=0, height=0)
        
        info_layout.add_widget(self.ids["progress_slider"])
        info_layout.add_widget(self.ids["current_time_label"])
        info_layout.add_widget(self.ids["total_time_label"])
        info_layout.add_widget(self.ids["play_pause_btn"])
        
        layout.add_widget(info_layout)
        self.add_widget(layout)

class DesktopRootLayout(MDBoxLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.orientation = "vertical"
        self.md_bg_color = "#000000"
        
        # Horizontal layout for Sidebar + Main Content
        horiz_layout = MDBoxLayout(orientation="horizontal")
        
        # SIDEBAR
        sidebar = MDBoxLayout(
            orientation="vertical",
            size_hint_x=None,
            width=dp(260),
            md_bg_color="#080808",
            padding=[dp(16), dp(24)],
            spacing=dp(8)
        )
        
        sidebar.add_widget(MDLabel(
            text="KIVY MUSIC",
            font_style="H4",
            bold=True,
            theme_text_color="Custom",
            text_color="#BB86FC",
            size_hint_y=None,
            height=dp(80),
            padding=[dp(12), 0]
        ))
        
        nav_layout = MDBoxLayout(orientation="vertical", spacing=dp(4), size_hint_y=None)
        nav_layout.bind(minimum_height=nav_layout.setter('height'))
        
        self.sidebar_home = DesktopSidebarItem(
            text="Inicio",
            icon="home",
            on_release=lambda x: MDApp.get_running_app().go_to_library() if MDApp.get_running_app() else None
        )
        self.sidebar_playlists = DesktopSidebarItem(
            text="Playlists",
            icon="playlist-music",
            on_release=lambda x: MDApp.get_running_app().go_to_playlists() if MDApp.get_running_app() else None
        )
        self.sidebar_offline = DesktopSidebarItem(
            text="Descargas",
            icon="download-circle",
            on_release=lambda x: MDApp.get_running_app().go_to_offline() if MDApp.get_running_app() else None
        )
        
        # Active binding
        Clock.schedule_once(lambda dt: MDApp.get_running_app().bind(current_screen=self._update_sidebar_active) if MDApp.get_running_app() else None)
        
        nav_layout.add_widget(self.sidebar_home)
        nav_layout.add_widget(self.sidebar_playlists)
        nav_layout.add_widget(self.sidebar_offline)
        sidebar.add_widget(nav_layout)
        
        sidebar.add_widget(MDLabel(
            text="PERSONALIZACIÓN",
            font_style="Overline",
            theme_text_color="Hint",
            size_hint_y=None,
            height=dp(40),
            padding=[dp(12), dp(20), 0, 0]
        ))
        
        theme_grid = MDGridLayout(cols=4, spacing=dp(8), size_hint_y=None, height=dp(40), padding=[dp(12), 0])
        for color in ["#BB86FC", "#00E676", "#2979FF", "#FF5252"]:
            btn = MDIconButton(
                icon="circle",
                theme_text_color="Custom",
                text_color=color,
                on_release=lambda x, c=color: MDApp.get_running_app().change_theme(c) if MDApp.get_running_app() else None
            )
            theme_grid.add_widget(btn)
        sidebar.add_widget(theme_grid)
        
        sidebar.add_widget(Widget()) # Spacer
        
        # Current Song Card in Sidebar
        side_card = MDCard(
            size_hint_y=None,
            height=dp(280),
            radius=[dp(16)],
            md_bg_color="#121212",
            orientation="vertical",
            padding=dp(8),
            spacing=dp(8)
        )
        self.ids["side_player_thumb"] = FitImage(radius=[dp(12)])
        self.ids["side_player_title"] = MDLabel(
            text="Reproduciendo ahora",
            bold=True,
            halign="center",
            font_style="Subtitle2",
            adaptive_height=True
        )
        side_card.add_widget(self.ids["side_player_thumb"])
        side_card.add_widget(self.ids["side_player_title"])
        sidebar.add_widget(side_card)
        
        horiz_layout.add_widget(sidebar)
        
        # MAIN CONTENT AREA
        main_content = MDBoxLayout(orientation="vertical", padding=[dp(24), dp(16), dp(24), 0])
        
        # TOP BAR
        top_bar = MDBoxLayout(size_hint_y=None, height=dp(64), spacing=dp(20))
        search_card = MDCard(
            size_hint_x=0.5,
            md_bg_color="#1A1A1A",
            radius=[dp(32)],
            padding=[dp(16), 0],
            elevation=0
        )
        search_box = MDBoxLayout(spacing=dp(12))
        search_box.add_widget(MDIcon(icon="magnify", theme_text_color="Custom", text_color="#B3B3B3", pos_hint={"center_y": 0.5}))
        self.ids["desktop_search_input"] = MDTextField(
            hint_text="Buscar canciones, artistas o álbumes...",
            mode="rectangle",
            fill_color_normal=[0,0,0,0],
            line_color_normal=[0,0,0,0],
            line_color_focus=[0,0,0,0]
        )
        self.ids["desktop_search_input"].bind(on_text_validate=lambda x: MDApp.get_running_app().search_songs(x.text) if MDApp.get_running_app() else None)
        search_box.add_widget(self.ids["desktop_search_input"])
        search_card.add_widget(search_box)
        top_bar.add_widget(search_card)
        top_bar.add_widget(Widget())
        top_bar.add_widget(MDIconButton(icon="account-circle", user_font_size="32sp", theme_text_color="Custom", text_color="#FFFFFF"))
        main_content.add_widget(top_bar)
        
        # SCREEN MANAGER
        self.ids["screen_manager"] = MDScreenManager()
        self.ids["screen_manager"].add_widget(DesktopScreenLibrary())
        self.ids["screen_manager"].add_widget(DesktopScreenPlaylists())
        self.ids["screen_manager"].add_widget(DesktopScreenOffline())
        self.ids["screen_manager"].add_widget(DesktopScreenPlayer())
        main_content.add_widget(self.ids["screen_manager"])
        
        horiz_layout.add_widget(main_content)
        self.add_widget(horiz_layout)
        
        # BOTTOM PLAYBACK BAR
        bottom_bar = MDBoxLayout(
            size_hint_y=None,
            height=dp(100),
            md_bg_color="#0F0F0F",
            padding=[dp(24), dp(8)],
            spacing=dp(32)
        )
        with bottom_bar.canvas.before:
            Color(1, 1, 1, 0.05)
            self.bottom_line = Line(width=1)
        bottom_bar.bind(pos=self._update_bottom_line, size=self._update_bottom_line)
        
        # Left: Song Info
        info_box = MDBoxLayout(size_hint_x=0.25, spacing=dp(16))
        self.ids["bottom_thumb"] = FitImage(size_hint=(None, None), size=(dp(64), dp(64)), radius=[dp(8)])
        info_labels = MDBoxLayout(orientation="vertical", pos_hint={"center_y": 0.5}, adaptive_height=True)
        self.ids["bottom_title"] = MDLabel(text="Ninguna canción", bold=True, font_style="Subtitle1", shorten=True)
        self.ids["bottom_artist"] = MDLabel(text="Artista", theme_text_color="Secondary", font_style="Caption", shorten=True)
        info_labels.add_widget(self.ids["bottom_title"])
        info_labels.add_widget(self.ids["bottom_artist"])
        info_box.add_widget(self.ids["bottom_thumb"])
        info_box.add_widget(info_labels)
        bottom_bar.add_widget(info_box)
        
        # Center: Main Controls
        controls_outer = MDBoxLayout(orientation="vertical", size_hint_x=0.5, spacing=dp(4))
        controls_inner = MDBoxLayout(pos_hint={"center_x": 0.5}, spacing=dp(24), adaptive_width=True)
        controls_inner.add_widget(MDIconButton(icon="shuffle", theme_text_color="Custom", text_color="#B3B3B3"))
        controls_inner.add_widget(MDIconButton(icon="skip-previous", user_font_size="30sp", on_release=lambda x: MDApp.get_running_app().on_previous() if MDApp.get_running_app() else None))
        self.ids["bottom_play_btn"] = MDIconButton(
            icon="play-circle",
            user_font_size="48sp",
            theme_text_color="Custom",
            text_color="#BB86FC",
            on_release=lambda x: MDApp.get_running_app().toggle_playback() if MDApp.get_running_app() else None
        )
        controls_inner.add_widget(self.ids["bottom_play_btn"])
        controls_inner.add_widget(MDIconButton(icon="skip-next", user_font_size="30sp", on_release=lambda x: MDApp.get_running_app().on_next() if MDApp.get_running_app() else None))
        controls_inner.add_widget(MDIconButton(icon="repeat", theme_text_color="Custom", text_color="#B3B3B3"))
        controls_outer.add_widget(controls_inner)
        
        progress_box = MDBoxLayout(spacing=dp(12))
        self.ids["bottom_current_time"] = MDLabel(text="0:00", font_style="Caption", size_hint_x=None, width=dp(40), halign="right")
        self.ids["bottom_progress"] = MDSlider(min=0, max=100, value=0, color="#BB86FC", hint=False)
        self.ids["bottom_total_time"] = MDLabel(text="0:00", font_style="Caption", size_hint_x=None, width=dp(40))
        progress_box.add_widget(self.ids["bottom_current_time"])
        progress_box.add_widget(self.ids["bottom_progress"])
        progress_box.add_widget(self.ids["bottom_total_time"])
        controls_outer.add_widget(progress_box)
        bottom_bar.add_widget(controls_outer)
        
        # Right: Volume & Extra
        right_box = MDBoxLayout(size_hint_x=0.25, spacing=dp(12))
        right_box.add_widget(MDIcon(icon="volume-high", theme_text_color="Secondary", pos_hint={"center_y": 0.5}))
        self.ids["volume_slider"] = MDSlider(min=0, max=100, value=100, color="#BB86FC", size_hint_x=0.6, pos_hint={"center_y": 0.5})
        right_box.add_widget(self.ids["volume_slider"])
        right_box.add_widget(MDIconButton(icon="playlist-play", pos_hint={"center_y": 0.5}))
        right_box.add_widget(MDIconButton(icon="maximize", on_release=lambda x: MDApp.get_running_app().go_to_player() if MDApp.get_running_app() else None, pos_hint={"center_y": 0.5}))
        bottom_bar.add_widget(right_box)
        
        self.add_widget(bottom_bar)
        
        # Initial sidebar state (if app already has current_screen)
        def set_initial_state(dt):
            app = MDApp.get_running_app()
            if app and hasattr(app, 'current_screen'):
                self._update_sidebar_active(app, app.current_screen)
        Clock.schedule_once(set_initial_state)

    def _update_bottom_line(self, instance, value):
        self.bottom_line.points = [instance.x, instance.top, instance.right, instance.top]

    def _update_sidebar_active(self, app, screen_name):
        self.sidebar_home.active = (screen_name == "library")
        self.sidebar_playlists.active = (screen_name == "playlists")
        self.sidebar_offline.active = (screen_name == "offline")

def get_desktop_ui():
    return DesktopRootLayout()

# Register classes in Factory for RecycleView and other lookups
Factory.register('DesktopPlaylistItem', cls=DesktopPlaylistItem)
Factory.register('DesktopOfflineItem', cls=DesktopOfflineItem)
Factory.register('DesktopSidebarItem', cls=DesktopSidebarItem)
Factory.register('DesktopSearchItem', cls=DesktopSearchItem)
Factory.register('DesktopScreenLibrary', cls=DesktopScreenLibrary)
Factory.register('DesktopScreenPlaylists', cls=DesktopScreenPlaylists)
Factory.register('DesktopScreenOffline', cls=DesktopScreenOffline)
Factory.register('DesktopScreenPlayer', cls=DesktopScreenPlayer)
Factory.register('DesktopRootLayout', cls=DesktopRootLayout)
