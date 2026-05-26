# VERSIÓN CORREGIDA - Separando código KV y Python

# ===================================================================
# PARTE 1: MODIFICACIONES AL ARCHIVO KV (ScreenLibrary)
# ===================================================================
# Reemplaza tu ScreenLibrary existente con esta versión:

"""
<ScreenLibrary>:
    name: "library"
    md_bg_color: "#000000"
    
    MDBoxLayout:
        orientation: "vertical"
        padding: [0, "56dp", 0, 0]
        
        MDTopAppBar:
            id: top_bar
            title: "Mi Biblioteca"
            anchor_title: "center"
            elevation: 0
            md_bg_color: "#000000"
            specific_text_color: "#BB86FC"
            left_action_items: []  # Se llenará dinámicamente
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
"""

# ===================================================================
# PARTE 2: FUNCIONES PARA AGREGAR A main.py
# ===================================================================

def update_top_bar(self, show_back=False, title="Mi Biblioteca"):
    """Actualizar la barra superior para mostrar/ocultar flecha de regreso"""
    try:
        top_bar = self.root.get_screen("library").ids.top_bar
        
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
        self.root.get_screen("library").ids.list_header.text = "RECOMENDADOS PARA TI"
        
        # Actualizar top bar para ocultar flecha
        self.update_top_bar(show_back=False)
        
        # Limpiar búsqueda
        try:
            self.root.get_screen("library").ids.search_input.text = ""
        except:
            pass
        
        # Cargar recommendations
        if self.recommendations_cache:
            self._update_results_rv(self.recommendations_cache, "RECOMENDADOS PARA TI")
        else:
            threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
            self.root.get_screen("library").ids.list_header.text = "CARGANDO RECOMENDACIONES..."
        
    except Exception as e:
        Logger.error(f"App: Error en back_to_recommendations: {e}")

def open_playlist(self, playlist_name):
    """Abrir playlist específica con flecha de regreso"""
    try:
        # Cargar playlist
        playlist_songs = self.playlists.get(playlist_name, [])
        
        # Actualizar top bar para mostrar flecha
        self.update_top_bar(show_back=True, title=playlist_name)
        
        # Actualizar header
        self.root.get_screen("library").ids.list_header.text = f"PLAYLIST: {playlist_name.upper()}"
        self.current_playlist_name = playlist_name
        
        # Cambiar modo
        self.library_mode = 'playlist'
        
        # Convertir a formato para RecycleView
        rv_data = []
        for i, song in enumerate(playlist_songs):
            rv_data.append({
                'title': song.get('title', 'Canción desconocida'),
                'artist': song.get('artist', 'Artista desconocido'),
                'thumbnail': song.get('thumbnail', ''),
                'song_data': song
            })
        
        self._update_results_rv(rv_data)
        self.root.current = 'library'
        
        Logger.info(f"App: Playlist abierta con flecha de regreso: {playlist_name}")
        
    except Exception as e:
        Logger.error(f"App: Error abriendo playlist: {e}")

def search_songs(self, query):
    """Búsqueda con flecha de regreso"""
    if not query or not query.strip():
        return
    
    # Mostrar spinner
    self.root.get_screen("library").ids.search_spinner.active = True
    self.root.get_screen("library").ids.list_header.text = "BUSCANDO..."
    
    # Actualizar top bar para mostrar flecha
    self.update_top_bar(show_back=True, title=f"Buscar: {query}")
    
    # Cambiar modo
    self.library_mode = 'search'
    
    # Búsqueda normal
    try:
        results = search_youtube(query, limit=20)
        
        if results:
            self.last_results = results
            self.root.get_screen("library").ids.list_header.text = f"RESULTADOS ({len(results)})"
            
            # Convertir a formato para RecycleView
            rv_data = []
            for i, res in enumerate(results):
                rv_data.append({
                    'title': res['title'],
                    'artist': res['artist'],
                    'thumbnail': res['thumbnail'],
                    'song_data': res
                })
            
            self._update_results_rv(rv_data)
            
        else:
            self.root.get_screen("library").ids.list_header.text = "SIN RESULTADOS"
            self._update_results_rv([])
            
    except Exception as e:
        Logger.error(f"App: Error en búsqueda: {e}")
        self.root.get_screen("library").ids.list_header.text = "ERROR EN BÚSQUEDA"
    
    finally:
        self.root.get_screen("library").ids.search_spinner.active = False

def go_to_playlists(self):
    """Ir a pantalla de playlists - resetear top bar"""
    self.root.transition = SlideTransition(direction="left")
    self.root.current = "playlists"
    self.display_playlists()

def go_to_offline(self):
    """Ir a música offline - resetear top bar"""
    self.root.transition = SlideTransition(direction="right")
    self.root.current = "offline"
    self.load_offline_songs()

def _return_to_recommendations(self):
    """Regresar a recommendations - resetear top bar"""
    try:
        # Resetear modo a recommendations
        self.library_mode = 'recommendations'
        
        # Resetear top bar
        self.update_top_bar(show_back=False)
        
        # Actualizar UI
        self.root.get_screen("library").ids.list_header.text = "RECOMENDADOS PARA TI"
        
        # Limpiar búsqueda
        try:
            self.root.get_screen("library").ids.search_input.text = ""
        except:
            pass
        
        # Cargar recommendations
        if self.recommendations_cache:
            self._update_results_rv(self.recommendations_cache, "RECOMENDADOS PARA TI")
        else:
            threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
            self.root.get_screen("library").ids.list_header.text = "CARGANDO RECOMENDACIONES..."
        
        Logger.info("App: Regresando a RECOMENDADOS PARA TI")
        
    except Exception as e:
        Logger.error(f"App: Error regresando a recommendations: {e}")

def _fetch_recommendations_thread(self):
    """Cargar recommendations - resetear top bar"""
    try:
        from extractor import get_recommendations
        results = get_recommendations()
        
        if results:
            self.recommendations_cache = results
            
            # Actualizar UI en el main thread
            Clock.schedule_once(lambda dt: self._on_recommendations_loaded(results))
            
    except Exception as e:
        Logger.error(f"App: Error cargando recommendations: {e}")
        Clock.schedule_once(lambda dt: self._on_recommendations_error())

def _on_recommendations_loaded(self, results):
    """Cuando las recommendations están cargadas"""
    try:
        # Asegurarse que el top bar esté reseteado
        self.update_top_bar(show_back=False)
        
        # Actualizar header
        self.root.get_screen("library").ids.list_header.text = "RECOMENDADOS PARA TI"
        
        # Convertir a formato para RecycleView
        rv_data = []
        for i, res in enumerate(results):
            rv_data.append({
                'title': res['title'],
                'artist': res['artist'],
                'thumbnail': res['thumbnail'],
                'song_data': res
            })
        
        self._update_results_rv(rv_data)
        Logger.info(f"App: {len(results)} recomendaciones cargadas")
        
    except Exception as e:
        Logger.error(f"App: Error procesando recommendations: {e}")

def _on_recommendations_error(self):
    """Cuando hay error cargando recommendations"""
    try:
        self.update_top_bar(show_back=False)
        self.root.get_screen("library").ids.list_header.text = "ERROR CARGANDO"
        self._update_results_rv([])
    except Exception as e:
        Logger.error(f"App: Error en recommendations error: {e}")

def on_key(self, window, key, *args):
    """Back button handler con reset de top bar"""
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
            
            # NUEVO: Si volvemos a library, siempre mostrar recommendations y resetear top bar
            if screen_back_map[current] == 'library':
                self._return_to_recommendations()
            
            return True
        
        # Priority 4: On library screen - siempre regresar a recommendations
        if current == 'library':
            self._return_to_recommendations()
            return True
        
        return False
    return False

# ===================================================================
# INSTRUCCIONES DE INTEGRACIÓN:
# ===================================================================

"""
PASO 1: En tu archivo .kv, reemplaza la sección <ScreenLibrary> completa 
        con el código KV que está entre comillas triples al principio.

PASO 2: En tu main.py, agrega todas las funciones Python de este archivo 
        (desde update_top_bar hasta on_key).

PASO 3: Reemplaza tus funciones existentes (open_playlist, search_songs, etc.)
        con las versiones modificadas de este archivo.

PASO 4: ¡Listo! Ahora tendrás una flecha de regreso visible en las playlists.

RESULTADO:
- En recommendations: "Mi Biblioteca" (sin flecha)
- En playlist: "← NOMBRE_PLAYLIST" (con flecha)
- Click en flecha: vuelve a recommendations
"""
