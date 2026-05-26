# SIMPLE NAVIGATION FIX - Siempre regresar a RECOMENDADOS PARA TI

# 1. MODIFICAR on_key en main.py - Reemplazar la función existente

def on_key(self, window, key, *args):
    """Back button handler: siempre regresar a recommendations desde library"""
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
            
            # NUEVO: Si volvemos a library, siempre mostrar recommendations
            if screen_back_map[current] == 'library':
                self._return_to_recommendations()
            
            return True
        
        # Priority 4: On library screen - siempre regresar a recommendations
        if current == 'library':
            self._return_to_recommendations()
            return True
        
        return False
    return False

# 2. AGREGAR esta función helper

def _return_to_recommendations(self):
    """Siempre regresar a la pantalla de recomendaciones"""
    try:
        # Resetear modo a recommendations
        self.library_mode = 'recommendations'
        
        # Actualizar UI
        self.root.get_screen("library").ids.list_header.text = "RECOMENDADOS PARA TI"
        
        # Limpiar búsqueda
        try:
            self.root.get_screen("library").ids.search_input.text = ""
        except:
            pass
        
        # Cargar recommendations
        if self.recommendations_cache:
            # Si hay cache, mostrarlo inmediatamente
            self._update_results_rv(self.recommendations_cache, "RECOMENDADOS PARA TI")
        else:
            # Si no hay cache, cargar desde YouTube
            threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
            self.root.get_screen("library").ids.list_header.text = "CARGANDO RECOMENDACIONES..."
        
        Logger.info("App: Regresando a RECOMENDADOS PARA TI")
        
    except Exception as e:
        Logger.error(f"App: Error regresando a recommendations: {e}")

# 3. MODIFICAR go_to_playlists para que regrese a recommendations

def go_to_playlists(self):
    """Ir a pantalla de playlists"""
    self.root.transition = SlideTransition(direction="left")
    self.root.current = "playlists"
    self.display_playlists()

# 4. MODIFICAR go_to_offline para que regrese a recommendations

def go_to_offline(self):
    """Ir a música offline"""
    self.root.transition = SlideTransition(direction="right")
    self.root.current = "offline"
    self.load_offline_songs()

# 5. MODIFICAR open_playlist para que no guarde estado

def open_playlist(self, playlist_name):
    """Abrir playlist específica - siempre regresa a recommendations"""
    try:
        # Cargar playlist
        playlist_songs = self.playlists.get(playlist_name, [])
        
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

# 6. MANTENER search_songs como está, pero asegurarse que regrese a recommendations

def search_songs(self, query):
    """Búsqueda - siempre puede regresar a recommendations"""
    if not query or not query.strip():
        return
    
    # Mostrar spinner
    self.root.get_screen("library").ids.search_spinner.active = True
    self.root.get_screen("library").ids.list_header.text = "BUSCANDO..."
    
    # Cambiar modo a search
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

# 7. ASEGURARSE que los botones de navegación funcionen correctamente

# Si tienes botones personalizados, asegúrate que llamen a _return_to_recommendations:

def on_custom_back_button(self):
    """Botón de back personalizado - siempre a recommendations"""
    self._return_to_recommendations()

def on_home_button(self):
    """Botón de home - siempre a recommendations"""
    self._return_to_recommendations()

# 8. OPCIONAL: Agregar confirmación si está reproduciendo música

def _return_to_recommendations(self):
    """Siempre regresar a la pantalla de recomendaciones"""
    try:
        # Si está reproduciendo música, preguntar si desea continuar
        if hasattr(self, 'player') and self.player and self.player.is_playing():
            self._show_continue_playing_dialog()
        else:
            self._do_return_to_recommendations()
        
    except Exception as e:
        Logger.error(f"App: Error regresando a recommendations: {e}")
        self._do_return_to_recommendations()

def _do_return_to_recommendations(self):
    """Ejecutar el regreso a recommendations"""
    try:
        # Resetear modo a recommendations
        self.library_mode = 'recommendations'
        
        # Actualizar UI
        self.root.get_screen("library").ids.list_header.text = "RECOMENDADOS PARA TI"
        
        # Limpiar búsqueda
        try:
            self.root.get_screen("library").ids.search_input.text = ""
        except:
            pass
        
        # Cargar recommendations
        if self.recommendations_cache:
            # Si hay cache, mostrarlo inmediatamente
            self._update_results_rv(self.recommendations_cache, "RECOMENDADOS PARA TI")
        else:
            # Si no hay cache, cargar desde YouTube
            threading.Thread(target=self._fetch_recommendations_thread, daemon=True).start()
            self.root.get_screen("library").ids.list_header.text = "CARGANDO RECOMENDACIONES..."
        
        Logger.info("App: Regresando a RECOMENDADOS PARA TI")
        
    except Exception as e:
        Logger.error(f"App: Error ejecutando retorno a recommendations: {e}")

def _show_continue_playing_dialog(self):
    """Mostrar diálogo preguntando si continuar reproduciendo"""
    try:
        from kivymd.uix.dialog import MDDialog
        from kivymd.uix.button import MDFlatButton
        
        dialog = MDDialog(
            title="Música reproduciéndose",
            text="¿Deseas continuar reproduciendo mientras navegas?",
            buttons=[
                MDFlatButton(
                    text="CONTINUAR",
                    on_release=lambda x: self._continue_and_return()
                ),
                MDFlatButton(
                    text="DETENER",
                    on_release=lambda x: self._stop_and_return()
                )
            ]
        )
        dialog.open()
        
    except Exception as e:
        Logger.error(f"App: Error mostrando diálogo: {e}")
        self._do_return_to_recommendations()

def _continue_and_return(self):
    """Continuar reproduciendo y regresar a recommendations"""
    try:
        # Cerrar diálogo
        if hasattr(self, '_continue_dialog'):
            self._continue_dialog.dismiss()
        
        # Regresar sin detener música
        self._do_return_to_recommendations()
        
    except Exception as e:
        Logger.error(f"App: Error continuando y regresando: {e}")

def _stop_and_return(self):
    """Detener música y regresar a recommendations"""
    try:
        # Cerrar diálogo
        if hasattr(self, '_continue_dialog'):
            self._continue_dialog.dismiss()
        
        # Detener música
        if hasattr(self, 'player') and self.player:
            self.player.stop()
        
        # Regresar
        self._do_return_to_recommendations()
        
    except Exception as e:
        Logger.error(f"App: Error deteniendo y regresando: {e}")

# RESUMEN DEL COMPORTAMIENTO:

# 📱 Flujo de navegación:
# 1. Estás en "RECOMENDADOS PARA TI"
# 2. Entras a "PLAYLIST: FAVORITOS"  
# 3. Le das back → Vuelve a "RECOMENDADOS PARA TI" ✅

# 1. Estás en "RECOMENDADOS PARA TI"
# 2. Buscas "Bad Bunny" → "RESULTADOS (20)"
# 3. Entras a "PLAYLIST: CARRETERA"
# 4. Le das back → Vuelve a "RECOMENDADOS PARA TI" ✅

# 1. Estás en "RECOMENDADOS PARA TI"
# 2. Entras a "PLAYLISTS"
# 3. Entras a "PLAYLIST: ROMÁNTICA"
# 4. Le das back → Vuelve a "RECOMENDADOS PARA TI" ✅

# SIEMPRE vuelve a la pantalla principal de recommendations, sin importar el camino.
