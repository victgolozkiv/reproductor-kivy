import sqlite3
import json
import math
import re
import threading
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
from collections import defaultdict, Counter
from kivy.logger import Logger
from kivy.clock import Clock
from concurrent.futures import ThreadPoolExecutor

@dataclass
class SearchResult:
    song_id: int
    title: str
    artist: str
    album: str
    thumbnail_url: str
    youtube_url: str
    relevance_score: float
    match_type: str  # 'exact', 'fuzzy', 'related_artist', 'same_album'
    artist_id: int
    popularity_score: float

class KivySearchEngine:
    """Motor de búsqueda optimizado para Kivy con soporte asíncrono"""
    
    def __init__(self, db_path: str, app_instance=None):
        self.db_path = db_path
        self.app = app_instance
        self.conn = None
        self.executor = ThreadPoolExecutor(max_workers=2)
        self.cache = {}
        self.cache_lock = threading.Lock()
        self._init_db()
        
    def _init_db(self):
        """Inicializar conexión y crear tablas optimizadas para Kivy"""
        try:
            self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self.conn.row_factory = sqlite3.Row
            self._create_optimized_tables()
            Logger.info("KivySearchEngine: Base de datos inicializada correctamente")
        except Exception as e:
            Logger.error(f"KivySearchEngine: Error inicializando DB: {e}")
            
    def _create_optimized_tables(self):
        """Crear esquema optimizado para el reproductor Kivy"""
        cursor = self.conn.cursor()
        
        # Tabla de canciones con metadatos enriquecidos
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS songs (
                song_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist_id INTEGER NOT NULL,
                album_id INTEGER,
                youtube_url TEXT UNIQUE,
                youtube_id TEXT UNIQUE,
                duration INTEGER,
                thumbnail_url TEXT,
                audio_stream_url TEXT,
                bpm INTEGER,
                key_signature TEXT,
                energy_level REAL,
                danceability REAL,
                acousticness REAL,
                instrumentalness REAL,
                valence REAL,
                popularity_score REAL DEFAULT 0.0,
                play_count INTEGER DEFAULT 0,
                last_played TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(artist_id),
                FOREIGN KEY (album_id) REFERENCES albums(album_id)
            )
        """)
        
        # Tabla de artistas
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS artists (
                artist_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                normalized_name TEXT NOT NULL,
                genre_id INTEGER,
                country TEXT,
                popularity_score REAL DEFAULT 0.0,
                monthly_listeners INTEGER,
                image_url TEXT,
                bio TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (genre_id) REFERENCES genres(genre_id)
            )
        """)
        
        # Tabla de álbumes
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS albums (
                album_id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                artist_id INTEGER NOT NULL,
                release_year INTEGER,
                genre_id INTEGER,
                cover_url TEXT,
                track_count INTEGER DEFAULT 0,
                popularity_score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (artist_id) REFERENCES artists(artist_id),
                FOREIGN KEY (genre_id) REFERENCES genres(genre_id)
            )
        """)
        
        # Tabla de géneros
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS genres (
                genre_id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                parent_genre_id INTEGER,
                description TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (parent_genre_id) REFERENCES genres(genre_id)
            )
        """)
        
        # Tabla de interacciones del usuario
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_interactions (
                interaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id TEXT,
                song_id INTEGER NOT NULL,
                interaction_type TEXT,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                session_id TEXT,
                context TEXT,
                FOREIGN KEY (song_id) REFERENCES songs(song_id)
            )
        """)
        
        # Tabla de perfil de usuario
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_profile (
                user_id TEXT PRIMARY KEY,
                favorite_genres TEXT,
                favorite_artists TEXT,
                avg_session_duration REAL,
                preferred_bpm_range TEXT,
                preferred_energy_range TEXT,
                discovery_taste REAL DEFAULT 0.5,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Índices optimizados para búsqueda
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_songs_title ON songs(title)",
            "CREATE INDEX IF NOT EXISTS idx_songs_artist_id ON songs(artist_id)",
            "CREATE INDEX IF NOT EXISTS idx_songs_popularity ON songs(popularity_score DESC)",
            "CREATE INDEX IF NOT EXISTS idx_artists_normalized_name ON artists(normalized_name)",
            "CREATE INDEX IF NOT EXISTS idx_user_interactions_song_id ON user_interactions(song_id)",
            "CREATE INDEX IF NOT EXISTS idx_user_interactions_timestamp ON user_interactions(timestamp DESC)",
            "CREATE INDEX IF NOT EXISTS idx_songs_composite ON songs(artist_id, popularity_score DESC)"
        ]
        
        for idx in indexes:
            cursor.execute(idx)
            
        self.conn.commit()
        Logger.info("KivySearchEngine: Tablas e índices creados correctamente")
    
    def _normalize_string(self, text: str) -> str:
        """Normalizar texto para búsqueda fuzzy"""
        if not text:
            return ""
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calcular distancia de Levenshtein optimizada"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = list(range(len(s2) + 1))
        
        for i, c1 in enumerate(s1):
            current_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = previous_row[j + 1] + 1
                deletions = current_row[j] + 1
                substitutions = previous_row[j] + (c1 != c2)
                current_row.append(min(insertions, deletions, substitutions))
            previous_row = current_row
        
        return previous_row[-1]
    
    def _similarity_score(self, s1: str, s2: str) -> float:
        """Calcular score de similitud (0-1)"""
        if not s1 or not s2:
            return 0.0
        
        # Levenshtein similarity
        lev_dist = self._levenshtein_distance(s1.lower(), s2.lower())
        max_len = max(len(s1), len(s2))
        lev_similarity = 1 - (lev_dist / max_len) if max_len > 0 else 0
        
        # Sequence matcher similarity
        seq_similarity = SequenceMatcher(None, s1.lower(), s2.lower()).ratio()
        
        # Weighted combination
        return (lev_similarity * 0.6) + (seq_similarity * 0.4)
    
    def _expand_query(self, query: str) -> List[str]:
        """Expander consulta con términos relacionados para música latina"""
        expansions = []
        words = query.split()
        
        # Agregar consulta original
        expansions.append(query)
        
        # Agregar palabras individuales
        for word in words:
            if len(word) > 2:
                expansions.append(word)
        
        # Variaciones específicas para música en español
        variations = {
            'rock': ['rock en español', 'rock latino', 'alternativo', 'pop rock'],
            'pop': ['pop latino', 'indie pop', 'synth pop', 'balada'],
            'trap': ['trap latino', 'trap malandro', 'drill', 'rap latino'],
            'reggaeton': ['reggaetón', 'latin trap', 'perreo', 'dembow'],
            'salsa': ['salsa cubana', 'salsa colombiana', 'timba', 'guaracha'],
            'bachata': ['bachata moderna', 'bachata urbana', 'bolero'],
            'cumbia': ['cumbia peruana', 'cumbia colombiana', 'cumbia villera', 'tecno cumbia'],
            'urbano': ['musica urbana', 'latino urbano', 'trap latino', 'reggaeton'],
            'romantica': ['balada', 'bolero', 'romance', 'love songs']
        }
        
        for word in words:
            word_lower = word.lower()
            if word_lower in variations:
                expansions.extend(variations[word_lower])
        
        return list(set(expansions))
    
    def search_songs_async(self, query: str, limit: int = 20, user_id: str = None, callback=None):
        """Búsqueda asíncrona optimizada para Kivy"""
        def _search():
            try:
                results = self.search_songs(query, limit, user_id)
                if callback and self.app:
                    Clock.schedule_once(lambda dt: callback(results))
            except Exception as e:
                Logger.error(f"KivySearchEngine: Error en búsqueda asíncrona: {e}")
                if callback and self.app:
                    Clock.schedule_once(lambda dt: callback([]))
        
        self.executor.submit(_search)
    
    def search_songs(self, query: str, limit: int = 20, user_id: str = None) -> List[SearchResult]:
        """Búsqueda principal con Query Expansion y Fuzzy Search"""
        if not query.strip():
            return []
        
        cache_key = f"{query}_{limit}_{user_id}"
        
        # Check cache
        with self.cache_lock:
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        cursor = self.conn.cursor()
        results = []
        
        try:
            # 1. Query Expansion
            expanded_queries = self._expand_query(query)
            normalized_query = self._normalize_string(query)
            
            # 2. Exact matches (highest priority)
            exact_matches = self._search_exact_matches(cursor, expanded_queries, limit)
            results.extend(exact_matches)
            
            # 3. Fuzzy matches
            if len(results) < limit:
                fuzzy_matches = self._search_fuzzy_matches(
                    cursor, normalized_query, limit - len(results)
                )
                results.extend(fuzzy_matches)
            
            # 4. Artist-related expansion
            if len(results) < limit:
                artist_matches = self._search_artist_related(
                    cursor, results, limit - len(results)
                )
                results.extend(artist_matches)
            
            # 5. Personalization based on user history
            if user_id:
                results = self._personalize_results(cursor, user_id, results)
            
            # 6. Sort by relevance and limit
            results.sort(key=lambda x: x.relevance_score, reverse=True)
            results = results[:limit]
            
            # Cache results
            with self.cache_lock:
                self.cache[cache_key] = results
            
            Logger.info(f"KivySearchEngine: Búsqueda '{query}' encontró {len(results)} resultados")
            
        except Exception as e:
            Logger.error(f"KivySearchEngine: Error en búsqueda: {e}")
        
        return results
    
    def _search_exact_matches(self, cursor: sqlite3.Cursor, queries: List[str], limit: int) -> List[SearchResult]:
        """Búsqueda de coincidencias exactas optimizada"""
        results = []
        seen_songs = set()
        
        for query in queries[:3]:  # Limitar para rendimiento
            try:
                sql = """
                SELECT s.*, a.name as artist_name, al.title as album_title
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                LEFT JOIN albums al ON s.album_id = al.album_id
                WHERE s.title LIKE ? OR a.name LIKE ?
                ORDER BY s.popularity_score DESC
                LIMIT ?
                """
                cursor.execute(sql, (f'%{query}%', f'%{query}%', limit))
                
                for row in cursor.fetchall():
                    if row['song_id'] not in seen_songs:
                        seen_songs.add(row['song_id'])
                        relevance = self._calculate_relevance_score(
                            query, row['title'], row['artist_name'], 'exact'
                        )
                        
                        result = SearchResult(
                            song_id=row['song_id'],
                            title=row['title'],
                            artist=row['artist_name'],
                            album=row['album_title'] or 'Unknown Album',
                            thumbnail_url=row['thumbnail_url'] or '',
                            youtube_url=row['youtube_url'] or '',
                            relevance_score=relevance,
                            match_type='exact',
                            artist_id=row['artist_id'],
                            popularity_score=row['popularity_score'] or 0.0
                        )
                        results.append(result)
                        
                        if len(results) >= limit:
                            break
                            
            except Exception as e:
                Logger.warning(f"KivySearchEngine: Error en búsqueda exacta: {e}")
        
        return results
    
    def _search_fuzzy_matches(self, cursor: sqlite3.Cursor, normalized_query: str, limit: int) -> List[SearchResult]:
        """Búsqueda fuzzy optimizada para rendimiento"""
        results = []
        
        try:
            # Get candidate songs (limit for performance)
            sql = """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            ORDER BY s.popularity_score DESC
            LIMIT 100
            """
            cursor.execute(sql)
            candidates = cursor.fetchall()
            
            fuzzy_results = []
            
            for row in candidates:
                title_similarity = self._similarity_score(
                    normalized_query, 
                    self._normalize_string(row['title'])
                )
                artist_similarity = self._similarity_score(
                    normalized_query, 
                    self._normalize_string(row['artist_name'])
                )
                
                # Use the higher similarity score
                best_similarity = max(title_similarity, artist_similarity)
                
                if best_similarity > 0.6:  # Threshold for fuzzy matching
                    popularity = row['popularity_score'] or 0.0
                    relevance = best_similarity * 0.7 + (popularity / 100) * 0.3
                    fuzzy_results.append((relevance, row))
            
            # Sort by relevance and take top results
            fuzzy_results.sort(key=lambda x: x[0], reverse=True)
            
            for relevance, row in fuzzy_results[:limit]:
                result = SearchResult(
                    song_id=row['song_id'],
                    title=row['title'],
                    artist=row['artist_name'],
                    album=row['album_title'] or 'Unknown Album',
                    thumbnail_url=row['thumbnail_url'] or '',
                    youtube_url=row['youtube_url'] or '',
                    relevance_score=relevance,
                    match_type='fuzzy',
                    artist_id=row['artist_id'],
                    popularity_score=row['popularity_score'] or 0.0
                )
                results.append(result)
                
        except Exception as e:
            Logger.warning(f"KivySearchEngine: Error en búsqueda fuzzy: {e}")
        
        return results
    
    def _search_artist_related(self, cursor: sqlite3.Cursor, existing_results: List[SearchResult], limit: int) -> List[SearchResult]:
        """Expandir resultados con canciones del mismo artista"""
        results = []
        
        try:
            # Get unique artist IDs from existing results
            artist_ids = list(set(r.artist_id for r in existing_results[:5]))  # Top 5 artists
            excluded_songs = [r.song_id for r in existing_results]
            
            for artist_id in artist_ids:
                placeholders = ','.join(['?' for _ in excluded_songs])
                
                sql = f"""
                SELECT s.*, a.name as artist_name, al.title as album_title
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                LEFT JOIN albums al ON s.album_id = al.album_id
                WHERE s.artist_id = ? AND s.song_id NOT IN ({placeholders})
                ORDER BY s.popularity_score DESC
                LIMIT 3
                """
                
                cursor.execute(sql, [artist_id] + excluded_songs)
                
                for row in cursor.fetchall():
                    popularity = row['popularity_score'] or 0.0
                    relevance = 0.6 + (popularity / 100) * 0.4
                    
                    result = SearchResult(
                        song_id=row['song_id'],
                        title=row['title'],
                        artist=row['artist_name'],
                        album=row['album_title'] or 'Unknown Album',
                        thumbnail_url=row['thumbnail_url'] or '',
                        youtube_url=row['youtube_url'] or '',
                        relevance_score=relevance,
                        match_type='related_artist',
                        artist_id=row['artist_id'],
                        popularity_score=popularity
                    )
                    results.append(result)
                    
        except Exception as e:
            Logger.warning(f"KivySearchEngine: Error en búsqueda por artista: {e}")
        
        return results[:limit]
    
    def _calculate_relevance_score(self, query: str, title: str, artist: str, match_type: str) -> float:
        """Calcular score de relevancia para un resultado"""
        base_scores = {
            'exact': 1.0,
            'fuzzy': 0.7,
            'related_artist': 0.6,
            'same_album': 0.5
        }
        
        base_score = base_scores.get(match_type, 0.5)
        
        # Boost for exact title matches
        if query.lower() in title.lower():
            base_score += 0.2
        
        # Boost for artist matches
        if query.lower() in artist.lower():
            base_score += 0.15
        
        return min(base_score, 1.0)
    
    def _personalize_results(self, cursor: sqlite3.Cursor, user_id: str, results: List[SearchResult]) -> List[SearchResult]:
        """Personalizar resultados basados en el historial del usuario"""
        try:
            # Get user profile
            cursor.execute("SELECT * FROM user_profile WHERE user_id = ?", (user_id,))
            user_profile = cursor.fetchone()
            
            if not user_profile:
                return results
            
            # Parse preferences
            try:
                favorite_genres = json.loads(user_profile['favorite_genres'] or '[]')
                favorite_artists = json.loads(user_profile['favorite_artists'] or '[]')
            except:
                favorite_genres = []
                favorite_artists = []
            
            # Boost scores based on preferences
            for result in results:
                # Get song genres
                cursor.execute("""
                    SELECT g.name FROM genres g
                    JOIN artist_genres ag ON g.genre_id = ag.genre_id
                    WHERE ag.artist_id = ?
                """, (result.artist_id,))
                
                song_genres = [row[0] for row in cursor.fetchall()]
                
                # Boost for favorite genres
                genre_boost = 0.1 if any(g in favorite_genres for g in song_genres) else 0
                
                # Boost for favorite artists
                artist_boost = 0.15 if result.artist_id in favorite_artists else 0
                
                # Apply boosts
                result.relevance_score += genre_boost + artist_boost
            
            return results
            
        except Exception as e:
            Logger.warning(f"KivySearchEngine: Error personalizando resultados: {e}")
            return results
    
    def add_song_from_youtube(self, title: str, artist: str, youtube_url: str, thumbnail_url: str = '', duration: int = 0):
        """Agregar canción desde YouTube a la base de datos local"""
        cursor = self.conn.cursor()
        
        try:
            # Get or create artist
            cursor.execute("SELECT artist_id FROM artists WHERE name = ?", (artist,))
            artist_row = cursor.fetchone()
            
            if artist_row:
                artist_id = artist_row['artist_id']
            else:
                cursor.execute("""
                    INSERT INTO artists (name, normalized_name, popularity_score)
                    VALUES (?, ?, ?)
                """, (artist, self._normalize_string(artist), 50.0))
                artist_id = cursor.lastrowid
            
            # Check if song already exists
            cursor.execute("SELECT song_id FROM songs WHERE youtube_url = ?", (youtube_url,))
            if cursor.fetchone():
                Logger.info(f"KivySearchEngine: La canción ya existe: {title}")
                return
            
            # Add song
            cursor.execute("""
                INSERT INTO songs (title, artist_id, youtube_url, thumbnail_url, duration, popularity_score)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title, artist_id, youtube_url, thumbnail_url, duration, 60.0))
            
            song_id = cursor.lastrowid
            self.conn.commit()
            
            Logger.info(f"KivySearchEngine: Canción agregada: {title} (ID: {song_id})")
            return song_id
            
        except Exception as e:
            Logger.error(f"KivySearchEngine: Error agregando canción: {e}")
            self.conn.rollback()
            return None
    
    def update_user_interaction(self, user_id: str, song_id: int, interaction_type: str):
        """Actualizar interacción del usuario para aprendizaje"""
        cursor = self.conn.cursor()
        
        try:
            # Record interaction
            cursor.execute("""
                INSERT INTO user_interactions (user_id, song_id, interaction_type, timestamp)
                VALUES (?, ?, ?, datetime('now'))
            """, (user_id, song_id, interaction_type))
            
            # Update song play count
            if interaction_type == 'play':
                cursor.execute("""
                    UPDATE songs SET play_count = play_count + 1, last_played = datetime('now')
                    WHERE song_id = ?
                """, (song_id,))
            
            self.conn.commit()
            
        except Exception as e:
            Logger.error(f"KivySearchEngine: Error actualizando interacción: {e}")
    
    def get_artist_songs(self, artist_id: int, limit: int = 20) -> List[SearchResult]:
        """Obtener canciones populares de un artista específico"""
        cursor = self.conn.cursor()
        
        try:
            sql = """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            WHERE s.artist_id = ?
            ORDER BY s.popularity_score DESC, s.play_count DESC
            LIMIT ?
            """
            
            cursor.execute(sql, (artist_id, limit))
            results = []
            
            for row in cursor.fetchall():
                result = SearchResult(
                    song_id=row['song_id'],
                    title=row['title'],
                    artist=row['artist_name'],
                    album=row['album_title'] or 'Unknown Album',
                    thumbnail_url=row['thumbnail_url'] or '',
                    youtube_url=row['youtube_url'] or '',
                    relevance_score=row['popularity_score'] / 100,
                    match_type='related_artist',
                    artist_id=row['artist_id'],
                    popularity_score=row['popularity_score'] or 0.0
                )
                results.append(result)
            
            return results
            
        except Exception as e:
            Logger.error(f"KivySearchEngine: Error obteniendo canciones del artista: {e}")
            return []
    
    def close(self):
        """Cerrar conexión y liberar recursos"""
        try:
            if self.executor:
                self.executor.shutdown(wait=False)
            if self.conn:
                self.conn.close()
            Logger.info("KivySearchEngine: Conexión cerrada correctamente")
        except Exception as e:
            Logger.error(f"KivySearchEngine: Error cerrando conexión: {e}")
