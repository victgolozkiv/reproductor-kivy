# MEJORAS DE NAVEGACIÓN PARA MAIN.PY - Sistema de navegación con pila de estados

# 1. MODIFICAR el __init__ de MusicPlayerApp (agregar después de las variables existentes)

def __init__(self, **kwargs):
    super().__init__(**kwargs)
    # ... tu código existente ...
    
    # NUEVO: Sistema de navegación con pila de estados
    self.navigation_stack = []  # Pila para mantener historial de navegación
    self.library_state = {
        'mode': 'recommendations',  # 'recommendations', 'search', 'playlist', 'offline', 'artist'
        'title': 'RECOMENDADOS PARA TI',
        'data': [],  # Datos actuales mostrados
        'playlist_name': '',  # Nombre de playlist actual
        'search_query': '',  # Query de búsqueda actual
        'artist_id': None,  # ID del artista actual
        'can_go_back': False  # Si se puede regresar al estado anterior
    }
    
    # ... resto de tu código existente ...

# 2. REEMPLAZAR completamente la función on_key con esta versión mejorada

def on_key(self, window, key, *args):
    """Back button handler: navegación inteligente con pila de estados."""
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
        
        # Priority 4: Navegación inteligente en pantalla principal
        if current == 'library':
            return self._handle_library_back()
        
        return False
    return False

def _handle_library_back(self):
    """Manejar navegación hacia atrás en la pantalla de biblioteca"""
    try:
        # Si tenemos un estado anterior en la pila, regresar a él
        if self.navigation_stack:
            previous_state = self.navigation_stack.pop()
            self._restore_library_state(previous_state)
            return True
        
        # Si no hay pila pero podemos regresar al estado anterior
        if self.library_state['can_go_back']:
            self._go_back_to_previous_library_state()
            return True
        
        # Si estamos en modo diferente a recommendations y no hay pila
        if self.library_state['mode'] != 'recommendations':
            self._return_to_recommendations()
            return True
        
        # Si ya estamos en recommendations, mostrar diálogo de salida
        self._show_exit_dialog()
        return True
        
    except Exception as e:
        Logger.error(f"App: Error en navegación hacia atrás: {e}")
        return False

def _go_back_to_previous_library_state(self):
    """Regresar al estado anterior de la biblioteca"""
    try:
        current_mode = self.library_state['mode']
        
        if current_mode == 'search':
            # De búsqueda a recommendations
            self._return_to_recommendations()
            
        elif current_mode == 'playlist':
            # De playlist a recommendations o al estado anterior
            if self.navigation_stack:
                previous_state = self.navigation_stack.pop()
                self._restore_library_state(previous_state)
            else:
                self._return_to_recommendations()
                
        elif current_mode == 'artist':
            # De artista a estado anterior
            if self.navigation_stack:
                previous_state = self.navigation_stack.pop()
                self._restore_library_state(previous_state)
            else:
                self._return_to_recommendations()
                
        elif current_mode == 'offline':
            # De offline a recommendations
            self._return_to_recommendations()
            
    except Exception as e:
        Logger.error(f"App: Error regresando al estado anterior: {e}")

def _return_to_recommendations(self):
    """Regresar a la pantalla de recomendaciones"""
    try:
        # Guardar estado actual en la pila si no es recommendations
        if self.library_state['mode'] != 'recommendations':
            self.navigation_stack.append(self.library_state.copy())
        
        # Cambiar a recommendations
        self.library_state['mode'] = 'recommendations'
        self.library_state['title'] = 'RECOMENDADOS PARA TI'
        self.library_state['can_go_back'] = len(self.navigation_stack) > 0
        
        # Actualizar UI
        self.root.get_screen("library").ids.list_header.text = "RECOMENDADOS PARA TI"
        
        # Limpiar búsqueda
        try:
            self.root.get_screen("library").ids.search_input.text = ""
        except:
            pass
        
        # Cargar recommendations
        if self.recommendations_cache:
            self._update_results_rv_recommendations(self.recommendations_cache)
        else:
            threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
            
        Logger.info("App: Regresando a recomendaciones")
        
    except Exception as e:
        Logger.error(f"App: Error regresando a recommendations: {e}")

def _restore_library_state(self, state):
    """Restaurar un estado específico de la biblioteca"""
    try:
        # Restaurar estado
        self.library_state = state.copy()
        
        # Actualizar UI según el modo
        if state['mode'] == 'search':
            self.root.get_screen("library").ids.list_header.text = f"RESULTADOS ({len(state['data'])})"
            self.root.get_screen("library").ids.search_input.text = state.get('search_query', '')
            self._update_results_rv(state['data'])
            
        elif state['mode'] == 'playlist':
            playlist_name = state.get('playlist_name', 'Playlist')
            self.root.get_screen("library").ids.list_header.text = f"PLAYLIST: {playlist_name.upper()}"
            self._update_results_rv(state['data'])
            
        elif state['mode'] == 'artist':
            artist_name = state.get('artist_name', 'Artista')
            self.root.get_screen("library").ids.list_header.text = f"MÁS DE {artist_name.upper()}"
            self._update_results_rv(state['data'])
            
        elif state['mode'] == 'offline':
            self.root.get_screen("library").ids.list_header.text = "MÚSICA DESCARGADA"
            self._update_results_rv(state['data'])
            
        elif state['mode'] == 'recommendations':
            self.root.get_screen("library").ids.list_header.text = "RECOMENDADOS PARA TI"
            if self.recommendations_cache:
                self._update_results_rv_recommendations(self.recommendations_cache)
        
        # Actualizar estado de navegación
        self.library_state['can_go_back'] = len(self.navigation_stack) > 0
        
        Logger.info(f"App: Estado restaurado: {state['mode']}")
        
    except Exception as e:
        Logger.error(f"App: Error restaurando estado: {e}")

# 3. MODIFICAR funciones de navegación existentes

def go_to_playlists(self):
    """Ir a pantalla de playlists guardando estado actual"""
    try:
        # Guardar estado actual si no es recommendations
        if self.library_state['mode'] != 'recommendations':
            self.navigation_stack.append(self.library_state.copy())
        
        # Navegar a playlists
        self.root.transition = SlideTransition(direction="left")
        self.root.current = "playlists"
        self.display_playlists()
        
    except Exception as e:
        Logger.error(f"App: Error yendo a playlists: {e}")

def go_to_offline(self):
    """Ir a música offline guardando estado actual"""
    try:
        # Guardar estado actual
        if self.library_state['mode'] != 'offline':
            self.navigation_stack.append(self.library_state.copy())
        
        # Actualizar estado a offline
        self.library_state['mode'] = 'offline'
        self.library_state['title'] = 'MÚSICA DESCARGADA'
        self.library_state['can_go_back'] = True
        
        # Navegar
        self.root.transition = SlideTransition(direction="right")
        self.root.current = "offline"
        self.load_offline_songs()
        
    except Exception as e:
        Logger.error(f"App: Error yendo a offline: {e}")

def open_playlist(self, playlist_name):
    """Abrir playlist específica guardando estado"""
    try:
        # Guardar estado actual
        self.navigation_stack.append(self.library_state.copy())
        
        # Cargar playlist
        playlist_songs = self.playlists.get(playlist_name, [])
        
        # Actualizar estado
        self.library_state['mode'] = 'playlist'
        self.library_state['title'] = f'Playlist: {playlist_name}'
        self.library_state['data'] = playlist_songs
        self.library_state['playlist_name'] = playlist_name
        self.library_state['can_go_back'] = True
        
        # Actualizar UI
        self.root.get_screen("library").ids.list_header.text = f"PLAYLIST: {playlist_name.upper()}"
        self.current_playlist_name = playlist_name
        
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
        
        Logger.info(f"App: Playlist abierta: {playlist_name}")
        
    except Exception as e:
        Logger.error(f"App: Error abriendo playlist: {e}")

def search_songs(self, query):
    """Búsqueda guardando estado anterior"""
    if not query or not query.strip():
        return
    
    # Guardar estado actual si no es search
    if self.library_state['mode'] != 'search':
        self.navigation_stack.append(self.library_state.copy())
    
    # Actualizar estado a search
    self.library_state['mode'] = 'search'
    self.library_state['title'] = f'Buscando: {query}'
    self.library_state['search_query'] = query
    self.library_state['can_go_back'] = True
    
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
        self._search_songs_fallback(query)

def _on_search_results_loaded(self, results):
    """Callback cuando los resultados de búsqueda están listos"""
    try:
        # Ocultar spinner
        self.root.get_screen("library").ids.search_spinner.active = False
        
        if results:
            self.last_results = results
            
            # Actualizar estado
            self.library_state['data'] = results
            self.library_state['title'] = f"RESULTADOS ({len(results)})"
            
            # Actualizar UI
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
                self.search_engine.update_user_interaction(self.user_id, 'search', self.library_state['search_query'])
                
        else:
            self.root.get_screen("library").ids.list_header.text = "SIN RESULTADOS"
            self._update_results_rv([])
            
    except Exception as e:
        Logger.error(f"App: Error procesando resultados de búsqueda: {e}")
        self.root.get_screen("library").ids.search_spinner.active = False

def on_artist_click(self, artist_name, artist_id):
    """Cuando el usuario hace click en un artista"""
    try:
        # Guardar estado actual
        self.navigation_stack.append(self.library_state.copy())
        
        # Buscar canciones del artista
        results = self.search_artist_songs(artist_id)
        
        if results:
            # Actualizar estado
            self.library_state['mode'] = 'artist'
            self.library_state['title'] = f'Artista: {artist_name}'
            self.library_state['data'] = results
            self.library_state['artist_name'] = artist_name
            self.library_state['artist_id'] = artist_id
            self.library_state['can_go_back'] = True
            
            # Actualizar UI
            self.root.get_screen("library").ids.list_header.text = f"MÁS DE {artist_name.upper()}"
            self.last_results = results
            self._update_results_rv(results)
            self.root.current = 'library'
            
            Logger.info(f"App: Vista de artista: {artist_name}")
        
    except Exception as e:
        Logger.error(f"App: Error en click de artista: {e}")

# 4. NUEVAS funciones de utilidad para navegación

def clear_navigation_stack(self):
    """Limpiar pila de navegación"""
    self.navigation_stack.clear()
    self.library_state['can_go_back'] = False
    Logger.info("App: Pila de navegación limpiada")

def get_navigation_history(self):
    """Obtener historial de navegación"""
    return {
        'current': self.library_state,
        'stack': self.navigation_stack.copy(),
        'can_go_back': self.library_state['can_go_back']
    }

def go_back_to_specific_mode(self, target_mode):
    """Regresar a un modo específico si existe en la pila"""
    try:
        # Buscar el estado más reciente con el modo objetivo
        for i in range(len(self.navigation_stack) - 1, -1, -1):
            if self.navigation_stack[i]['mode'] == target_mode:
                # Restaurar estados posteriores
                self.navigation_stack = self.navigation_stack[:i]
                # Restaurar el estado encontrado
                self._restore_library_state(self.navigation_stack.pop())
                return True
        
        # Si no se encontró, ir a recommendations
        self._return_to_recommendations()
        return False
        
    except Exception as e:
        Logger.error(f"App: Error regresando al modo {target_mode}: {e}")
        return False

# 5. MODIFICAR display_playlists para mantener navegación

def display_playlists(self):
    """Mostrar playlists manteniendo el contexto de navegación"""
    try:
        playlist_rv = self.root.get_screen("playlists").ids.playlists_rv
        playlist_data = []
        
        for name in self.playlists.keys():
            playlist_data.append({
                'text': name,
                'playlist_name': name
            })
        
        playlist_rv.data = playlist_data
        Logger.info(f"App: {len(playlist_data)} playlists mostradas")
        
    except Exception as e:
        Logger.error(f"App: Error mostrando playlists: {e}")

# 6. EJEMPLOS de uso en botones de la UI

# En tus callbacks de botones, ahora puedes:

def on_home_button_press(self):
    """Botón de home - regresar a recommendations limpiando pila"""
    self.clear_navigation_stack()
    self._return_to_recommendations()

def on_back_button_press(self):
    """Botón de back personalizado - same que on_key"""
    self._handle_library_back()

def on_breadcrumb_click(self, mode):
    """Click en breadcrumb de navegación"""
    self.go_back_to_specific_mode(mode)

# 7. ESTADO VISUAL - Opcional: agregar indicadores visuales

def update_navigation_indicators(self):
    """Actualizar indicadores visuales de navegación"""
    try:
        # Mostrar/ocultar botón de back según corresponda
        if hasattr(self, 'back_button'):
            self.back_button.opacity = 1 if self.library_state['can_go_back'] else 0.5
            self.back_button.disabled = not self.library_state['can_go_back']
        
        # Actualizar breadcrumb si existe
        if hasattr(self, 'breadcrumb_label'):
            breadcrumb_text = self._generate_breadcrumb()
            self.breadcrumb_label.text = breadcrumb_text
            
    except Exception as e:
        Logger.error(f"App: Error actualizando indicadores: {e}")

def _generate_breadcrumb(self):
    """Generar texto de breadcrumb"""
    try:
        parts = []
        
        # Agregar estado actual
        parts.append(self.library_state['title'])
        
        # Agregar estados anteriores en la pila (máximo 2)
        for state in self.navigation_stack[-2:]:
            parts.append(state['title'])
        
        return " ← ".join(reversed(parts))
        
    except:
        return self.library_state['title']
