from kivy.lang import Builder

DESKTOP_UI = '''
<PlaylistItem@MDCard>:
    md_bg_color: "#121212"
    radius: [12, 12, 12, 12]
    elevation: 2
    padding: [12, 10, 12, 10]
    on_release: app.open_playlist(root.text)
    
    MDBoxLayout:
        orientation: "horizontal"
        spacing: "12dp"
        MDIcon:
            icon: "playlist-music"
            theme_text_color: "Custom"
            text_color: "#BB86FC"
            font_size: "32sp"
            pos_hint: {"center_y": 0.5}
        MDLabel:
            text: root.text
            theme_text_color: "Custom"
            text_color: "#FFFFFF"
            bold: True
            pos_hint: {"center_y": 0.5}

<OfflineItem@MDCard>:
    md_bg_color: "#121212"
    radius: [12, 12, 12, 12]
    elevation: 2
    padding: [12, 8, 12, 8]
    on_release: app.play_local_song(root.index)
    
    MDBoxLayout:
        orientation: "horizontal"
        spacing: "12dp"
        MDIcon:
            icon: "music-note"
            theme_text_color: "Custom"
            text_color: "#BB86FC"
            font_size: "32sp"
            pos_hint: {"center_y": 0.5}
        MDBoxLayout:
            orientation: "vertical"
            MDLabel:
                text: root.title
                theme_text_color: "Custom"
                text_color: "#FFFFFF"
                bold: True
            MDLabel:
                text: root.artist
                theme_text_color: "Secondary"
                font_style: "Caption"

<SidebarItem@MDCard>:
    text: ""
    icon: ""
    active: False
    orientation: "horizontal"
    size_hint_y: None
    height: "50dp"
    md_bg_color: [1, 1, 1, 0.05] if self.active else [0, 0, 0, 0]
    radius: [12, 12, 12, 12]
    padding: ["12dp", 0, "12dp", 0]
    spacing: "12dp"
    ripple_behavior: True
    on_release: root.on_release() if hasattr(root, 'on_release') else None

    MDIcon:
        icon: root.icon
        theme_text_color: "Custom"
        text_color: "#BB86FC" if root.active else "#B3B3B3"
        pos_hint: {"center_y": 0.5}
        font_size: "24sp"
    
    MDLabel:
        text: root.text
        theme_text_color: "Custom"
        text_color: "#FFFFFF" if root.active else "#B3B3B3"
        bold: root.active
        font_style: "Button"
        pos_hint: {"center_y": 0.5}

<SearchItem@MDCard>:
    md_bg_color: "#181818"
    radius: [16, 16, 16, 16]
    elevation: 0
    padding: 0
    orientation: "vertical"
    ripple_behavior: True
    on_release: app.play_selected_song(root.index if hasattr(root, 'index') else 0)
    
    RelativeLayout:
        size_hint_y: None
        height: self.width
        
        AsyncImage:
            id: card_thumbnail
            source: root.thumbnail if hasattr(root, 'thumbnail') else ""
            allow_stretch: True
            keep_ratio: False
            # Optimized masking for sharpness
            canvas.before:
                Color:
                    rgba: 1, 1, 1, 1
                StencilPush
                RoundedRectangle:
                    pos: self.pos
                    size: self.size
                    radius: [16, 16, 0, 0]
                StencilUse
            canvas.after:
                StencilUnUse
                StencilPop
        
        # Overlay gradient for depth
        canvas.after:
            Color:
                rgba: 0, 0, 0, 0.1
            Rectangle:
                pos: self.pos
                size: self.size
    
    MDBoxLayout:
        orientation: "vertical"
        padding: ["12dp", "16dp", "12dp", "16dp"]
        spacing: "4dp"
        adaptive_height: True
        
        MDLabel:
            text: root.title if hasattr(root, 'title') else "Sin título"
            bold: True
            font_style: "H6"
            font_size: "16sp"
            theme_text_color: "Custom"
            text_color: "#FFFFFF"
            shorten: True
            shorten_from: "right"
            adaptive_height: True
        
        MDLabel:
            text: root.artist if hasattr(root, 'artist') else "YouTube Music"
            theme_text_color: "Custom"
            text_color: "#B3B3B3"
            font_style: "Caption"
            font_size: "13sp"
            shorten: True
            adaptive_height: True

<DesktopScreenLibrary@MDScreen>:
    name: "library"
    MDBoxLayout:
        orientation: "vertical"
        padding: [0, "20dp", 0, 0]
        spacing: "20dp"
        
        MDBoxLayout:
            adaptive_height: True
            spacing: "20dp"
            MDLabel:
                id: list_header
                text: "Recomendados para ti"
                font_style: "H5"
                bold: True
            MDSpinner:
                id: search_spinner
                size_hint: None, None
                size: dp(30), dp(30)
                active: False
                color: "#BB86FC"
        
        RecycleView:
            id: results_rv
            viewclass: 'SearchItem'
            RecycleGridLayout:
                cols: 4 # Desktop: More columns
                default_size: None, dp(240)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(20)
                padding: [0, 0, dp(20), dp(20)]

<DesktopScreenPlaylists@MDScreen>:
    name: "playlists"
    MDBoxLayout:
        orientation: "vertical"
        padding: [0, "20dp", 0, 0]
        spacing: "20dp"
        
        MDLabel:
            text: "Mis Playlists"
            font_style: "H5"
            bold: True
        
        RecycleView:
            id: playlists_rv
            viewclass: 'PlaylistItem'
            RecycleGridLayout:
                cols: 3
                default_size: None, dp(80)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                spacing: dp(16)

<DesktopScreenOffline@MDScreen>:
    name: "offline"
    MDBoxLayout:
        orientation: "vertical"
        padding: [0, "20dp", 0, 0]
        spacing: "20dp"
        
        MDLabel:
            text: "Música Descargada"
            font_style: "H5"
            bold: True
        
        RecycleView:
            id: offline_rv
            viewclass: 'OfflineItem'
            RecycleBoxLayout:
                default_size: None, dp(80)
                default_size_hint: 1, None
                size_hint_y: None
                height: self.minimum_height
                orientation: 'vertical'
                spacing: dp(8)

<DesktopScreenPlayer@MDScreen>:
    name: "player"
    MDBoxLayout:
        orientation: "horizontal"
        padding: "40dp"
        spacing: "60dp"
        
        # Big Album Art
        MDCard:
            size_hint: None, None
            size: "450dp", "450dp"
            radius: [24, 24, 24, 24]
            elevation: 8
            pos_hint: {"center_y": 0.5}
            FitImage:
                id: thumbnail
                source: ""
                radius: [24, 24, 24, 24]
                
        # Info & Lyrics
        MDBoxLayout:
            orientation: "vertical"
            spacing: "24dp"
            pos_hint: {"center_y": 0.5}
            
            MDLabel:
                id: song_title
                text: "Título de la canción"
                font_style: "H3"
                bold: True
                adaptive_height: True
            
            MDLabel:
                id: artist_name
                text: "Nombre del Artista"
                font_style: "H5"
                theme_text_color: "Secondary"
                adaptive_height: True
            
            MDBoxLayout:
                adaptive_height: True
                spacing: "16dp"
                MDIconButton:
                    icon: "heart-outline"
                    user_font_size: "32sp"
                MDIconButton:
                    icon: "playlist-plus"
                    user_font_size: "32sp"
            
            # Hidden for desktop as we have bottom bar, but keep IDs for compatibility
            MDSpinner:
                id: loading_spinner
                active: False
                size_hint: None, None
                size: "48dp", "48dp"
            
            # These are used by the code, but we prefer the bottom bar ones on desktop
            MDSlider:
                id: progress_slider
                opacity: 0
                size_hint_y: None
                height: 0
            MDLabel:
                id: current_time_label
                opacity: 0
                height: 0
            MDLabel:
                id: total_time_label
                opacity: 0
                height: 0
            MDIconButton:
                id: play_pause_btn
                opacity: 0
                height: 0

MDBoxLayout:
    orientation: "vertical"
    md_bg_color: "#000000"

    MDBoxLayout:
        orientation: "horizontal"
        
        # SIDEBAR
        MDBoxLayout:
            orientation: "vertical"
            size_hint_x: None
            width: "260dp"
            md_bg_color: "#080808"
            padding: ["16dp", "24dp", "16dp", "24dp"]
            spacing: "8dp"
            
            MDLabel:
                text: "KIVY MUSIC"
                font_style: "H4"
                bold: True
                theme_text_color: "Custom"
                text_color: "#BB86FC"
                size_hint_y: None
                height: "80dp"
                padding: ["12dp", 0]

            MDBoxLayout:
                orientation: "vertical"
                spacing: "4dp"
                size_hint_y: None
                height: self.minimum_height
                
                SidebarItem:
                    text: "Inicio"
                    icon: "home"
                    active: app.current_screen == "library"
                    on_release: app.go_to_library()
                
                SidebarItem:
                    text: "Playlists"
                    icon: "playlist-music"
                    active: app.current_screen == "playlists"
                    on_release: app.go_to_playlists()
                
                SidebarItem:
                    text: "Descargas"
                    icon: "download-circle"
                    active: app.current_screen == "offline"
                    on_release: app.go_to_offline()

            MDLabel:
                text: "PERSONALIZACIÓN"
                font_style: "Overline"
                theme_text_color: "Hint"
                size_hint_y: None
                height: "40dp"
                padding: ["12dp", "20dp", 0, 0]

            MDGridLayout:
                cols: 4
                spacing: "8dp"
                size_hint_y: None
                height: "40dp"
                padding: ["12dp", 0]
                
                MDIconButton:
                    icon: "circle"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.change_theme("#BB86FC")
                MDIconButton:
                    icon: "circle"
                    theme_text_color: "Custom"
                    text_color: "#00E676"
                    on_release: app.change_theme("#00E676")
                MDIconButton:
                    icon: "circle"
                    theme_text_color: "Custom"
                    text_color: "#2979FF"
                    on_release: app.change_theme("#2979FF")
                MDIconButton:
                    icon: "circle"
                    theme_text_color: "Custom"
                    text_color: "#FF5252"
                    on_release: app.change_theme("#FF5252")

            Widget: # Spacer
            
            # Current Song Card in Sidebar (Spotify Style)
            MDCard:
                size_hint_y: None
                height: "280dp"
                radius: [16, 16, 16, 16]
                md_bg_color: "#121212"
                orientation: "vertical"
                padding: "8dp"
                spacing: "8dp"
                
                FitImage:
                    id: side_player_thumb
                    source: ""
                    radius: [12, 12, 12, 12]
                
                MDLabel:
                    id: side_player_title
                    text: "Reproduciendo ahora"
                    bold: True
                    halign: "center"
                    font_style: "Subtitle2"
                    adaptive_height: True
        
        # MAIN CONTENT AREA
        MDBoxLayout:
            orientation: "vertical"
            padding: ["24dp", "16dp", "24dp", 0]
            
            # TOP BAR
            MDBoxLayout:
                size_hint_y: None
                height: "64dp"
                spacing: "20dp"
                
                MDCard:
                    size_hint_x: 0.5
                    md_bg_color: "#1A1A1A"
                    radius: [32, 32, 32, 32]
                    padding: ["16dp", 0, "16dp", 0]
                    elevation: 0
                    
                    MDBoxLayout:
                        spacing: "12dp"
                        MDIcon:
                            icon: "magnify"
                            theme_text_color: "Custom"
                            text_color: "#B3B3B3"
                            pos_hint: {"center_y": 0.5}
                        MDTextField:
                            id: desktop_search_input
                            hint_text: "Buscar canciones, artistas o álbumes..."
                            mode: "rectangle"
                            fill_color_normal: [0,0,0,0]
                            line_color_normal: [0,0,0,0]
                            line_color_focus: [0,0,0,0]
                            on_text_validate: app.search_songs(self.text)
                
                Widget:
                
                MDIconButton:
                    icon: "account-circle"
                    user_font_size: "32sp"
                    theme_text_color: "Custom"
                    text_color: "#FFFFFF"

            # SCREEN MANAGER
            MDScreenManager:
                id: screen_manager
                DesktopScreenLibrary:
                DesktopScreenPlaylists:
                DesktopScreenOffline:
                DesktopScreenPlayer:
    
    # BOTTOM PLAYBACK BAR
    MDBoxLayout:
        size_hint_y: None
        height: "100dp"
        md_bg_color: "#0F0F0F"
        padding: ["24dp", "8dp", "24dp", "8dp"]
        spacing: "32dp"
        
        canvas.before:
            Color:
                rgba: [1, 1, 1, 0.05]
            Line:
                points: [self.x, self.top, self.right, self.top]
                width: 1

        # Left: Song Info
        MDBoxLayout:
            size_hint_x: 0.25
            spacing: "16dp"
            FitImage:
                id: bottom_thumb
                size_hint: None, None
                size: "64dp", "64dp"
                radius: [8, 8, 8, 8]
                source: ""
            MDBoxLayout:
                orientation: "vertical"
                pos_hint: {"center_y": 0.5}
                adaptive_height: True
                MDLabel:
                    id: bottom_title
                    text: "Ninguna canción"
                    bold: True
                    font_style: "Subtitle1"
                    shorten: True
                MDLabel:
                    id: bottom_artist
                    text: "Artista"
                    theme_text_color: "Secondary"
                    font_style: "Caption"
                    shorten: True
        
        # Center: Main Controls
        MDBoxLayout:
            orientation: "vertical"
            size_hint_x: 0.5
            spacing: "4dp"
            
            MDBoxLayout:
                pos_hint: {"center_x": 0.5}
                spacing: "24dp"
                adaptive_width: True
                
                MDIconButton:
                    icon: "shuffle"
                    theme_text_color: "Custom"
                    text_color: "#B3B3B3"
                MDIconButton:
                    icon: "skip-previous"
                    user_font_size: "30sp"
                    on_release: app.on_previous()
                MDIconButton:
                    id: bottom_play_btn
                    icon: "play-circle"
                    user_font_size: "48sp"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.toggle_playback()
                MDIconButton:
                    icon: "skip-next"
                    user_font_size: "30sp"
                    on_release: app.on_next()
                MDIconButton:
                    icon: "repeat"
                    theme_text_color: "Custom"
                    text_color: "#B3B3B3"
            
            MDBoxLayout:
                spacing: "12dp"
                MDLabel:
                    id: bottom_current_time
                    text: "0:00"
                    font_style: "Caption"
                    size_hint_x: None
                    width: "40dp"
                    halign: "right"
                MDSlider:
                    id: bottom_progress
                    min: 0
                    max: 100
                    value: 0
                    color: "#BB86FC"
                    hint: False
                MDLabel:
                    id: bottom_total_time
                    text: "0:00"
                    font_style: "Caption"
                    size_hint_x: None
                    width: "40dp"
        
        # Right: Volume & Extra
        MDBoxLayout:
            size_hint_x: 0.25
            spacing: "12dp"
            MDIcon:
                icon: "volume-high"
                theme_text_color: "Secondary"
                pos_hint: {"center_y": 0.5}
            MDSlider:
                id: volume_slider
                min: 0
                max: 100
                value: 100
                color: "#BB86FC"
                size_hint_x: 0.6
                pos_hint: {"center_y": 0.5}
            MDIconButton:
                icon: "playlist-play"
                pos_hint: {"center_y": 0.5}
            MDIconButton:
                icon: "maximize"
                on_release: app.go_to_player()
                pos_hint: {"center_y": 0.5}

'''
