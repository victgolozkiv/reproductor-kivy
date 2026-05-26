# UI MODERNA INSPIRADA EN YOUTUBE MUSIC Y SPOTIFY
# Reemplaza completamente tu sección de Builder.load_string en main.py

'''
# =============================================================================
# PALETA DE COLORES MODERNA (AMOLED Optimizado)
# =============================================================================
# Fondo: Negro puro #000000
# Acento Primario: Púrpura Vibrante #BB86FC (como tienes)
# Acento Secundario: Rosa/Magenta #FF0266
# Gradientes: Púrpura a Rosa, Azul a Cyan
# Texto Principal: Blanco #FFFFFF
# Texto Secundario: Gris Medio #B3B3B3
# Superficies: Gris Oscuro #121212, #1E1E1E

# =============================================================================
# NUEVA ESTRUCTURA DE PANTALLAS
# =============================================================================
'''

MODERN_UI = '''
# =============================================================================
# COMPONENTES REUTILIZABLES
# =============================================================================

<ModernCard@MDCard>:
    md_bg_color: "#121212"
    radius: [16, 16, 16, 16]
    elevation: 0
    padding: "12dp"
    spacing: "8dp"

<GradientButton@MDIconButton>:
    canvas.before:
        Color:
            rgba: 0.737, 0.525, 0.988, 1  # #BB86FC
        RoundedRectangle:
            pos: self.pos
            size: self.size
            radius: [24, 24, 24, 24]
    md_bg_color: [0, 0, 0, 0]
    theme_text_color: "Custom"
    text_color: "#000000"
    size_hint: None, None
    size: "48dp", "48dp"

<GlowingIconButton@MDIconButton>:
    theme_text_color: "Custom"
    text_color: "#BB86FC"
    user_font_size: "24sp"
    canvas.after:
        Color:
            rgba: (0.737, 0.525, 0.988, 0.3) if self.state == 'down' else (0, 0, 0, 0)
        Ellipse:
            pos: self.center_x - 28, self.center_y - 28
            size: 56, 56

<SectionTitle@MDLabel>:
    theme_text_color: "Custom"
    text_color: "#FFFFFF"
    font_style: "H6"
    bold: True
    adaptive_height: True
    padding: [16, 16, 16, 8]

<SubsectionTitle@MDLabel>:
    theme_text_color: "Custom"
    text_color: "#B3B3B3"
    font_style: "Body2"
    adaptive_height: True
    padding: [16, 8, 16, 16]

<MoodChip@MDFlatButton>:
    md_bg_color: "#1E1E1E"
    theme_text_color: "Custom"
    text_color: "#FFFFFF"
    font_style: "Caption"
    size_hint: None, None
    height: "36dp"
    padding: [20, 8]
    radius: [18, 18, 18, 18]

# =============================================================================
# PANTALLA PRINCIPAL MODERNIZADA
# =============================================================================

<ScreenLibrary>:
    name: "library"
    md_bg_color: "#000000"
    
    MDBoxLayout:
        orientation: "vertical"
        
        # Top App Bar Moderno
        MDTopAppBar:
            id: top_bar
            title: "Mi Biblioteca"
            anchor_title: "left"
            elevation: 0
            md_bg_color: "#000000"
            specific_text_color: "#FFFFFF"
            left_action_items: []
            right_action_items: [["playlist-music", lambda x: app.go_to_playlists(), "Mis Playlists"], ["folder-music", lambda x: app.go_to_offline(), "Offline"]]
            
        # Barra de búsqueda moderna
        MDBoxLayout:
            size_hint_y: None
            height: "60dp"
            padding: [16, 8, 16, 8]
            
            MDCard:
                md_bg_color: "#1E1E1E"
                radius: [28, 28, 28, 28]
                elevation: 0
                padding: [16, 0, 16, 0]
                
                MDBoxLayout:
                    spacing: "12dp"
                    
                    MDIconButton:
                        icon: "magnify"
                        theme_text_color: "Custom"
                        text_color: "#B3B3B3"
                        user_font_size: "20sp"
                        size_hint: None, None
                        size: "40dp", "40dp"
                        pos_hint: {"center_y": 0.5}
                    
                    MDTextField:
                        id: search_input
                        hint_text: "Buscar canciones, artistas..."
                        mode: "rectangle"
                        fill_color_normal: [0, 0, 0, 0]
                        fill_color_focus: [0, 0, 0, 0]
                        line_color_normal: [0, 0, 0, 0]
                        line_color_focus: [0, 0, 0, 0]
                        hint_text_color_normal: "#B3B3B3"
                        hint_text_color_focus: "#BB86FC"
                        text_color_normal: "#FFFFFF"
                        text_color_focus: "#FFFFFF"
                        font_size: "16sp"
                        on_text_validate: app.search_songs(self.text)
                    
                    MDIconButton:
                        icon: "microphone"
                        theme_text_color: "Custom"
                        text_color: "#BB86FC"
                        user_font_size: "20sp"
                        size_hint: None, None
                        size: "40dp", "40dp"
                        pos_hint: {"center_y": 0.5}
                        on_release: app.on_mic_search()
        
        # Contenido scrolleable con secciones
        ScrollView:
            do_scroll_x: False
            bar_width: 0
            
            MDBoxLayout:
                id: main_content
                orientation: "vertical"
                adaptive_height: True
                padding: [0, 8, 0, 100]
                spacing: "24dp"
                
                # Header dinámico
                MDLabel:
                    id: list_header
                    text: "Recomendados para ti"
                    theme_text_color: "Custom"
                    text_color: "#FFFFFF"
                    font_style: "H5"
                    bold: True
                    adaptive_height: True
                    padding: [16, 16, 16, 8]
                
                # Sección: Escuchar de nuevo (Quick Picks)
                MDBoxLayout:
                    orientation: "vertical"
                    adaptive_height: True
                    
                    SectionTitle:
                        text: "Escuchar de nuevo"
                    
                    SubsectionTitle:
                        text: "Basado en tu historial reciente"
                    
                    # Chips de moods/géneros
                    MDBoxLayout:
                        size_hint_y: None
                        height: "48dp"
                        spacing: "12dp"
                        padding: [16, 0, 16, 0]
                        
                        MoodChip:
                            text: "🎵 Para ti"
                            md_bg_color: "#BB86FC"
                            text_color: "#000000"
                        
                        MoodChip:
                            text: "🔥 Éxitos"
                            on_release: app.search_songs("top hits 2024")
                        
                        MoodChip:
                            text: "🎸 Rock"
                            on_release: app.search_songs("rock en español")
                        
                        MoodChip:
                            text: "🎤 Pop"
                            on_release: app.search_songs("pop latino")
                        
                        MoodChip:
                            text: "🎧 Trap"
                            on_release: app.search_songs("trap latino")
                    
                    # Grid de canciones grandes (estilo YouTube Music)
                    RecycleView:
                        id: results_rv
                        viewclass: 'ModernSongCard'
                        size_hint_y: None
                        height: "280dp"
                        bar_width: 0
                        
                        RecycleGridLayout:
                            cols: 2
                            default_size: None, dp(260)
                            default_size_hint: 1, None
                            size_hint_y: None
                            height: self.minimum_height
                            spacing: dp(12)
                            padding: dp(16)
                
                # Spinner de carga
                MDSpinner:
                    id: search_spinner
                    size_hint: (None, None)
                    size: (dp(40), dp(40))
                    pos_hint: {'center_x': .5}
                    active: False
                    color: "#BB86FC"

    # Mini Player flotante (Bottom Sheet)
    MDFloatLayout:
        size_hint_y: None
        height: "80dp"
        pos_hint: {"bottom": 1}
        
        MDCard:
            id: mini_player
            md_bg_color: "#121212"
            radius: [24, 24, 0, 0]
            elevation: 8
            padding: [16, 12, 16, 12]
            opacity: 0  # Se muestra cuando hay música reproduciéndose
            
            MDBoxLayout:
                spacing: "12dp"
                
                # Thumbnail pequeño con animación de pulso
                FitImage:
                    id: mini_thumbnail
                    size_hint: None, None
                    size: "56dp", "56dp"
                    radius: [8, 8, 8, 8]
                    source: ""
                    
                    canvas.before:
                        Color:
                            rgba: (0.737, 0.525, 0.988, 0.5) if app.pulse_anim else (0, 0, 0, 0)
                        Line:
                            width: 2
                            ellipse: (self.x, self.y, self.width, self.height)
                
                # Info de la canción
                MDBoxLayout:
                    orientation: "vertical"
                    spacing: "4dp"
                    size_hint_x: 1
                    
                    MDLabel:
                        id: mini_title
                        text: "Título"
                        theme_text_color: "Custom"
                        text_color: "#FFFFFF"
                        font_style: "Subtitle1"
                        bold: True
                        shorten: True
                        shorten_from: "right"
                    
                    MDLabel:
                        id: mini_artist
                        text: "Artista"
                        theme_text_color: "Custom"
                        text_color: "#B3B3B3"
                        font_style: "Caption"
                        shorten: True
                
                # Controles
                MDBoxLayout:
                    size_hint_x: None
                    width: "120dp"
                    spacing: "8dp"
                    
                    GlowingIconButton:
                        icon: "skip-previous"
                        on_release: app.on_previous()
                    
                    MDFloatingActionButton:
                        id: mini_play_btn
                        icon: "play"
                        md_bg_color: "#FFFFFF"
                        theme_text_color: "Custom"
                        text_color: "#000000"
                        size_hint: None, None
                        size: "48dp", "48dp"
                        on_release: app.toggle_playback()
                    
                    GlowingIconButton:
                        icon: "skip-next"
                        on_release: app.on_next()
                
                # Botón expandir
                MDIconButton:
                    icon: "chevron-up"
                    theme_text_color: "Custom"
                    text_color: "#BB86FC"
                    on_release: app.go_to_player()

# =============================================================================
# NUEVA TARJETA DE CANCIÓN MODERNA (Estilo Spotify/YouTube Music)
# =============================================================================

<ModernSongCard@MDCard>:
    md_bg_color: "#0A0A0A"
    radius: [12, 12, 12, 12]
    elevation: 0
    padding: 0
    spacing: 0
    
    MDBoxLayout:
        orientation: "vertical"
        spacing: "8dp"
        
        # Imagen con overlay de gradiente
        RelativeLayout:
            size_hint_y: None
            height: "160dp"
            
            FitImage:
                id: card_thumbnail
                source: root.thumbnail if hasattr(root, 'thumbnail') else ""
                radius: [12, 12, 12, 12]
                allow_stretch: True
                keep_ratio: False
            
            # Gradient overlay
            canvas.after:
                Color:
                    rgba: 0, 0, 0, 0.3
                Rectangle:
                    pos: self.pos
                    size: self.size
            
            # Botón de play flotante (aparece en hover/press)
            MDIconButton:
                icon: "play-circle"
                theme_text_color: "Custom"
                text_color: "#BB86FC"
                user_font_size: "48sp"
                pos_hint: {"center_x": 0.5, "center_y": 0.5}
                md_bg_color: [0, 0, 0, 0.5]
                radius: [24, 24, 24, 24]
                opacity: 0.9
                on_release: app.play_selected_song(root.index if hasattr(root, 'index') else 0)
        
        # Info del texto
        MDBoxLayout:
            orientation: "vertical"
            spacing: "4dp"
            padding: [12, 8, 12, 12]
            adaptive_height: True
            
            MDLabel:
                text: root.title if hasattr(root, 'title') else "Título"
                theme_text_color: "Custom"
                text_color: "#FFFFFF"
                font_style: "Subtitle2"
                bold: True
                shorten: True
                shorten_from: "right"
                adaptive_height: True
            
            MDLabel:
                text: root.artist if hasattr(root, 'artist') else "Artista"
                theme_text_color: "Custom"
                text_color: "#B3B3B3"
                font_style: "Caption"
                shorten: True
                adaptive_height: True

# =============================================================================
# PANTALLA DE REPRODUCCIÓN FULL SCREEN (Estilo Spotify/YouTube Music)
# =============================================================================

<ScreenPlayer>:
    name: "player"
    md_bg_color: "#000000"
    
    # Fondo con blur y gradiente dinámico
    canvas.before:
        Color:
            rgba: 0.2, 0.1, 0.3, 0.3  # Gradiente púrpura sutil
        Rectangle:
            pos: self.pos
            size: self.size
    
    MDBoxLayout:
        orientation: "vertical"
        padding: [24, 16, 24, 24]
        spacing: "16dp"
        
        # Top bar
        MDBoxLayout:
            size_hint_y: None
            height: "56dp"
            
            MDIconButton:
                icon: "chevron-down"
                theme_text_color: "Custom"
                text_color: "#FFFFFF"
                on_release: app.go_to_library()
            
            Widget:
                size_hint_x: 1
            
            MDIconButton:
                icon: "dots-vertical"
                theme_text_color: "Custom"
                text_color: "#FFFFFF"
                on_release: app.show_song_options()
        
        # Contenido principal
        MDBoxLayout:
            orientation: "vertical"
            spacing: "24dp"
            
            # Album Art Grande con animación
            RelativeLayout:
                size_hint_y: None
                height: self.width  # Cuadrado perfecto
                
                # Sombra glow
                canvas.before:
                    Color:
                        rgba: (0.737, 0.525, 0.988, 0.2) if app.is_playing else (0, 0, 0, 0)
                    Ellipse:
                        pos: self.center_x - self.width/2 - 20, self.center_y - self.height/2 - 20
                        size: self.width + 40, self.height + 40
                
                FitImage:
                    id: thumbnail
                    source: ""
                    radius: [12, 12, 12, 12]
                    allow_stretch: True
                    keep_ratio: True
                    
                    canvas.before:
                        PushMatrix
                        Rotate:
                            angle: 0
                            origin: self.center
                        Color:
                            rgba: 0, 0, 0, 0.1
                        Rectangle:
                            pos: self.x + 10, self.y - 10
                            size: self.size
                    
                    canvas.after:
                        PopMatrix
            
            # Info de la canción
            MDBoxLayout:
                orientation: "vertical"
                spacing: "8dp"
                adaptive_height: True
                
                MDLabel:
                    id: song_title
                    text: "Título de la canción"
                    theme_text_color: "Custom"
                    text_color: "#FFFFFF"
                    font_style: "H5"
                    bold: True
                    halign: "center"
                    shorten: True
                    shorten_from: "right"
                    adaptive_height: True
                
                MDLabel:
                    id: artist_name
                    text: "Nombre del artista"
                    theme_text_color: "Custom"
                    text_color: "#B3B3B3"
                    font_style: "Subtitle1"
                    halign: "center"
                    adaptive_height: True
                
                # Botones de acción rápida
                MDBoxLayout:
                    size_hint_y: None
                    height: "48dp"
                    spacing: "32dp"
                    pos_hint: {"center_x": 0.5}
                    
                    MDIconButton:
                        icon: "heart-outline"
                        theme_text_color: "Custom"
                        text_color: "#BB86FC"
                        on_release: app.toggle_like()
                    
                    MDIconButton:
                        icon: "playlist-plus"
                        theme_text_color: "Custom"
                        text_color: "#BB86FC"
                        on_release: app.add_to_playlist_dialog()
                    
                    MDIconButton:
                        icon: "share-variant"
                        theme_text_color: "Custom"
                        text_color: "#BB86FC"
                        on_release: app.share_song()
            
            # Barra de progreso moderna
            MDBoxLayout:
                orientation: "vertical"
                size_hint_y: None
                height: "60dp"
                spacing: "8dp"
                
                # Slider de progreso
                MDSlider:
                    id: progress_slider
                    min: 0
                    max: 100
                    value: 0
                    hint: False
                    color: "#BB86FC"
                    track_color_active: "#BB86FC"
                    track_color_inactive: "#333333"
                    thumb_color: "#FFFFFF"
                    on_value: app.on_seek(self.value)
                
                # Tiempos
                MDBoxLayout:
                    MDLabel:
                        id: current_time
                        text: "0:00"
                        theme_text_color: "Custom"
                        text_color: "#B3B3B3"
                        font_style: "Caption"
                        halign: "left"
                    
                    Widget:
                        size_hint_x: 1
                    
                    MDLabel:
                        id: total_time
                        text: "3:45"
                        theme_text_color: "Custom"
                        text_color: "#B3B3B3"
                        font_style: "Caption"
                        halign: "right"
            
            # Controles principales
            MDBoxLayout:
                size_hint_y: None
                height: "80dp"
                spacing: "24dp"
                pos_hint: {"center_x": 0.5}
                
                # Shuffle
                MDIconButton:
                    id: shuffle_btn
                    icon: "shuffle"
                    theme_text_color: "Custom"
                    text_color: "#444444"
                    on_release: app.toggle_shuffle()
                
                # Previous
                MDIconButton:
                    icon: "skip-previous"
                    user_font_size: "40sp"
                    theme_text_color: "Custom"
                    text_color: "#FFFFFF"
                    on_release: app.on_previous()
                
                # Play/Pause principal
                MDFloatingActionButton:
                    id: play_pause_btn
                    icon: "play"
                    md_bg_color: "#FFFFFF"
                    theme_text_color: "Custom"
                    text_color: "#000000"
                    size_hint: None, None
                    size: "72dp", "72dp"
                    elevation: 4
                    on_release: app.toggle_playback()
                
                # Next
                MDIconButton:
                    icon: "skip-next"
                    user_font_size: "40sp"
                    theme_text_color: "Custom"
                    text_color: "#FFFFFF"
                    on_release: app.on_next()
                
                # Repeat
                MDIconButton:
                    id: repeat_btn
                    icon: "repeat"
                    theme_text_color: "Custom"
                    text_color: "#444444"
                    on_release: app.toggle_repeat()
            
            # Botón de lyrics (opcional)
            MDTextButton:
                text: "LYRICS"
                theme_text_color: "Custom"
                text_color: "#BB86FC"
                pos_hint: {"center_x": 0.5}
                on_release: app.show_lyrics()

# =============================================================================
# PANTALLA DE PLAYLISTS MODERNIZADA
# =============================================================================

<ScreenPlaylists>:
    name: "playlists"
    md_bg_color: "#000000"
    
    MDBoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            title: "Mis Playlists"
            anchor_title: "left"
            elevation: 0
            md_bg_color: "#000000"
            specific_text_color: "#FFFFFF"
            left_action_items: [["arrow-left", lambda x: app.back_to_recommendations()]]
            right_action_items: [["plus", lambda x: app.create_playlist_dialog()]]
        
        ScrollView:
            bar_width: 0
            
            MDBoxLayout:
                id: playlists_container
                orientation: "vertical"
                adaptive_height: True
                padding: [16, 16, 16, 16]
                spacing: "12dp"
                
                RecycleView:
                    id: playlists_rv
                    viewclass: 'ModernPlaylistCard'
                    size_hint_y: None
                    height: "500dp"
                    bar_width: 0
                    
                    RecycleGridLayout:
                        cols: 2
                        default_size: None, dp(160)
                        default_size_hint: 1, None
                        size_hint_y: None
                        height: self.minimum_height
                        spacing: dp(12)
                        padding: dp(0)

<ModernPlaylistCard@MDCard>:
    md_bg_color: "#121212"
    radius: [16, 16, 16, 16]
    elevation: 0
    padding: "16dp"
    
    MDBoxLayout:
        orientation: "vertical"
        spacing: "12dp"
        
        # Icono de playlist
        MDIcon:
            icon: "playlist-music"
            theme_text_color: "Custom"
            text_color: "#BB86FC"
            font_size: "48sp"
            halign: "center"
        
        MDLabel:
            text: root.text if hasattr(root, 'text') else "Playlist"
            theme_text_color: "Custom"
            text_color: "#FFFFFF"
            font_style: "H6"
            bold: True
            halign: "center"
            shorten: True
        
        MDLabel:
            text: f"{root.song_count if hasattr(root, 'song_count') else 0} canciones"
            theme_text_color: "Custom"
            text_color: "#B3B3B3"
            font_style: "Caption"
            halign: "center"

# =============================================================================
# PANTALLA OFFLINE MODERNIZADA
# =============================================================================

<ScreenOffline>:
    name: "offline"
    md_bg_color: "#000000"
    
    MDBoxLayout:
        orientation: "vertical"
        
        MDTopAppBar:
            title: "Descargas"
            anchor_title: "left"
            elevation: 0
            md_bg_color: "#000000"
            specific_text_color: "#FFFFFF"
            left_action_items: [["arrow-left", lambda x: app.back_to_recommendations()]]
        
        ScrollView:
            bar_width: 0
            
            RecycleView:
                id: offline_rv
                viewclass: 'ModernOfflineItem'
                
                RecycleBoxLayout:
                    default_size: None, dp(80)
                    default_size_hint: 1, None
                    size_hint_y: None
                    height: self.minimum_height
                    orientation: 'vertical'
                    spacing: dp(8)
                    padding: [16, 8, 16, 8]

<ModernOfflineItem@MDCard>:
    md_bg_color: "#0A0A0A"
    radius: [12, 12, 12, 12]
    elevation: 0
    padding: "12dp"
    
    MDBoxLayout:
        spacing: "12dp"
        
        FitImage:
            source: root.thumbnail if hasattr(root, 'thumbnail') else ""
            size_hint: None, None
            size: "56dp", "56dp"
            radius: [8, 8, 8, 8]
        
        MDBoxLayout:
            orientation: "vertical"
            spacing: "4dp"
            size_hint_x: 1
            
            MDLabel:
                text: root.title if hasattr(root, 'title') else "Título"
                theme_text_color: "Custom"
                text_color: "#FFFFFF"
                font_style: "Subtitle1"
                bold: True
                shorten: True
            
            MDLabel:
                text: root.artist if hasattr(root, 'artist') else "Artista"
                theme_text_color: "Custom"
                text_color: "#B3B3B3"
                font_style: "Caption"
                shorten: True
        
        MDIconButton:
            icon: "play"
            theme_text_color: "Custom"
            text_color: "#BB86FC"
            on_release: app.play_local_song(root.index if hasattr(root, 'index') else 0)

# =============================================================================
# ITEMS DE BUSQUEDA (SearchItem mejorado)
# =============================================================================

<SearchItem>:
    divider: None
    ripple_alpha: 0.1
    
    ImageLeftWidget:
        source: root.thumbnail
        radius: [8, 8, 8, 8]
        size_hint: None, None
        size: "48dp", "48dp"
    
    IRightBodyTouch:
        MDIconButton:
            icon: "play-circle"
            theme_text_color: "Custom"
            text_color: "#BB86FC"
            on_release: app.play_selected_song(root.index)

# =============================================================================
# MANAGER DE PANTALLAS
# =============================================================================

<ScreenManager>:
    ScreenLibrary:
    ScreenPlayer:
    ScreenPlaylists:
    ScreenOffline:
'''

# Para usar esta UI moderna, reemplaza completamente tu Builder.load_string() actual
# con: Builder.load_string(MODERN_UI)
