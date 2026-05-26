import sqlite3
import json
import math
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from difflib import SequenceMatcher
from collections import defaultdict
import threading

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

class FuzzySearchEngine:
    """Motor de búsqueda avanzado con Query Expansion y Fuzzy Search"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._init_db()
        self.cache = {}
        self.cache_lock = threading.Lock()
    
    def _init_db(self):
        """Inicializar conexión a base de datos"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_indexes()
    
    def _create_indexes(self):
        """Crear índices para optimizar búsquedas"""
        cursor = self.conn.cursor()
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_songs_title_fts ON songs(title)",
            "CREATE INDEX IF NOT EXISTS idx_artists_name_fts ON artists(name)",
            "CREATE INDEX IF NOT EXISTS idx_songs_composite ON songs(artist_id, popularity_score DESC)",
        ]
        for idx in indexes:
            cursor.execute(idx)
        self.conn.commit()
    
    def _normalize_string(self, text: str) -> str:
        """Normalizar texto para búsqueda fuzzy"""
        # Remove special characters, convert to lowercase
        normalized = re.sub(r'[^\w\s]', '', text.lower())
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized).strip()
        return normalized
    
    def _levenshtein_distance(self, s1: str, s2: str) -> int:
        """Calcular distancia de Levenshtein para fuzzy search"""
        if len(s1) < len(s2):
            return self._levenshtein_distance(s2, s1)
        
        if len(s2) == 0:
            return len(s1)
        
        previous_row = range(len(s2) + 1)
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
        """Expander consulta con términos relacionados"""
        expansions = []
        
        # Split into words
        words = query.split()
        
        # Add original query
        expansions.append(query)
        
        # Add individual words
        for word in words:
            if len(word) > 2:  # Skip very short words
                expansions.append(word)
        
        # Add common variations
        variations = {
            'rock': ['rock en español', 'rock latino', 'alternativo'],
            'pop': ['pop latino', 'indie pop', 'synth pop'],
            'trap': ['trap latino', 'trap malandro', 'drill'],
            'reggaeton': ['reggaetón', 'latin trap', 'perreo'],
        }
        
        for word in words:
            word_lower = word.lower()
            if word_lower in variations:
                expansions.extend(variations[word_lower])
        
        return list(set(expansions))  # Remove duplicates
    
    def search_songs(self, query: str, limit: int = 20, user_id: str = None) -> List[SearchResult]:
        """
        Búsqueda principal con Query Expansion y Fuzzy Search
        
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados
            user_id: ID del usuario para personalización
        
        Returns:
            Lista de resultados ordenados por relevancia
        """
        cache_key = f"{query}_{limit}_{user_id}"
        
        # Check cache
        with self.cache_lock:
            if cache_key in self.cache:
                return self.cache[cache_key]
        
        cursor = self.conn.cursor()
        results = []
        
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
        
        return results
    
    def _search_exact_matches(self, cursor: sqlite3.Cursor, queries: List[str], limit: int) -> List[SearchResult]:
        """Búsqueda de coincidencias exactas"""
        results = []
        
        for query in queries[:3]:  # Limit to prevent too many queries
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
                relevance = self._calculate_relevance_score(
                    query, row['title'], row['artist_name'], 'exact'
                )
                
                result = SearchResult(
                    song_id=row['song_id'],
                    title=row['title'],
                    artist=row['artist_name'],
                    album=row['album_title'] or 'Unknown Album',
                    thumbnail_url=row['thumbnail_url'],
                    youtube_url=row['youtube_url'],
                    relevance_score=relevance,
                    match_type='exact',
                    artist_id=row['artist_id'],
                    popularity_score=row['popularity_score']
                )
                results.append(result)
        
        return results
    
    def _search_fuzzy_matches(self, cursor: sqlite3.Cursor, normalized_query: str, limit: int) -> List[SearchResult]:
        """Búsqueda con coincidencias aproximadas"""
        results = []
        
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
            title_similarity = self._similarity_score(normalized_query, self._normalize_string(row['title']))
            artist_similarity = self._similarity_score(normalized_query, self._normalize_string(row['artist_name']))
            
            # Use the higher similarity score
            best_similarity = max(title_similarity, artist_similarity)
            
            if best_similarity > 0.6:  # Threshold for fuzzy matching
                relevance = best_similarity * 0.7 + (row['popularity_score'] / 100) * 0.3
                
                fuzzy_results.append((relevance, row))
        
        # Sort by relevance and take top results
        fuzzy_results.sort(key=lambda x: x[0], reverse=True)
        
        for relevance, row in fuzzy_results[:limit]:
            result = SearchResult(
                song_id=row['song_id'],
                title=row['title'],
                artist=row['artist_name'],
                album=row['album_title'] or 'Unknown Album',
                thumbnail_url=row['thumbnail_url'],
                youtube_url=row['youtube_url'],
                relevance_score=relevance,
                match_type='fuzzy',
                artist_id=row['artist_id'],
                popularity_score=row['popularity_score']
            )
            results.append(result)
        
        return results
    
    def _search_artist_related(self, cursor: sqlite3.Cursor, existing_results: List[SearchResult], limit: int) -> List[SearchResult]:
        """Expandir resultados con canciones del mismo artista"""
        results = []
        
        # Get unique artist IDs from existing results
        artist_ids = list(set(r.artist_id for r in existing_results[:5]))  # Top 5 artists
        
        for artist_id in artist_ids:
            sql = """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            WHERE s.artist_id = ? AND s.song_id NOT IN (?)
            ORDER BY s.popularity_score DESC
            LIMIT 3
            """
            
            # Exclude already found songs
            existing_song_ids = [r.song_id for r in existing_results]
            placeholders = ','.join(['?' for _ in existing_song_ids])
            
            cursor.execute(sql.replace('(?)', f'({placeholders})'), 
                          [artist_id] + existing_song_ids)
            
            for row in cursor.fetchall():
                relevance = 0.6 + (row['popularity_score'] / 100) * 0.4
                
                result = SearchResult(
                    song_id=row['song_id'],
                    title=row['title'],
                    artist=row['artist_name'],
                    album=row['album_title'] or 'Unknown Album',
                    thumbnail_url=row['thumbnail_url'],
                    youtube_url=row['youtube_url'],
                    relevance_score=relevance,
                    match_type='related_artist',
                    artist_id=row['artist_id'],
                    popularity_score=row['popularity_score']
                )
                results.append(result)
        
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
            favorite_genres = json.loads(user_profile['favorite_genres'] or '[]')
            favorite_artists = json.loads(user_profile['favorite_artists'] or '[]')
            
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
            print(f"Error personalizing results: {e}")
            return results
    
    def get_artist_songs(self, artist_id: int, limit: int = 20) -> List[SearchResult]:
        """Obtener canciones populares de un artista específico"""
        cursor = self.conn.cursor()
        
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
                thumbnail_url=row['thumbnail_url'],
                youtube_url=row['youtube_url'],
                relevance_score=row['popularity_score'] / 100,
                match_type='related_artist',
                artist_id=row['artist_id'],
                popularity_score=row['popularity_score']
            )
            results.append(result)
        
        return results
    
    def update_user_interaction(self, user_id: str, song_id: int, interaction_type: str):
        """Actualizar interacción del usuario para aprendizaje"""
        cursor = self.conn.cursor()
        
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
    
    def close(self):
        """Cerrar conexión a base de datos"""
        if self.conn:
            self.conn.close()
