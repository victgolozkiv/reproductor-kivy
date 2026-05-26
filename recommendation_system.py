import sqlite3
import json
import math
import random
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
from collections import defaultdict, Counter
import threading
from datetime import datetime, timedelta

@dataclass
class Recommendation:
    song_id: int
    title: str
    artist: str
    album: str
    thumbnail_url: str
    youtube_url: str
    recommendation_score: float
    recommendation_type: str  # 'content_based', 'collaborative', 'trending', 'discovery'
    reason: str  # Explicación para el usuario
    artist_id: int

class ContentBasedRecommender:
    """Sistema de recomendación basado en contenido y comportamiento del usuario"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.conn = None
        self._init_db()
        self.user_cache = {}
        self.cache_lock = threading.Lock()
    
    def _init_db(self):
        """Inicializar conexión y crear tablas necesarias"""
        self.conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._create_recommendation_tables()
    
    def _create_recommendation_tables(self):
        """Crear tablas específicas para el sistema de recomendación"""
        cursor = self.conn.cursor()
        
        # Tabla de similitud entre canciones (pre-calculada)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS song_similarity (
                song_id_1 INTEGER,
                song_id_2 INTEGER,
                similarity_score REAL,
                last_calculated TIMESTAMP,
                PRIMARY KEY (song_id_1, song_id_2),
                FOREIGN KEY (song_id_1) REFERENCES songs(song_id),
                FOREIGN KEY (song_id_2) REFERENCES songs(song_id)
            )
        """)
        
        # Tabla de recommendations cache
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recommendations_cache (
                user_id TEXT,
                song_id INTEGER,
                recommendation_score REAL,
                recommendation_type TEXT,
                reason TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, song_id),
                FOREIGN KEY (song_id) REFERENCES songs(song_id)
            )
        """)
        
        # Índices
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_song_similarity_score ON song_similarity(similarity_score DESC)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_recommendations_cache_score ON recommendations_cache(recommendation_score DESC)")
        
        self.conn.commit()
    
    def get_recommendations(self, user_id: str, limit: int = 20, context: str = 'general') -> List[Recommendation]:
        """
        Obtener recomendaciones personalizadas para un usuario
        
        Args:
            user_id: ID del usuario
            limit: Número máximo de recomendaciones
            context: Contexto de la recomendación ('search', 'player', 'home')
        
        Returns:
            Lista de recomendaciones ordenadas por score
        """
        cursor = self.conn.cursor()
        
        # 1. Obtener perfil del usuario
        user_profile = self._get_user_profile(cursor, user_id)
        
        # 2. Obtener historial reciente
        recent_songs = self._get_recent_songs(cursor, user_id, limit=50)
        
        if not recent_songs and not user_profile:
            # Nuevo usuario - recomendaciones populares
            return self._get_trending_recommendations(cursor, limit)
        
        recommendations = []
        
        # 3. Content-based recommendations
        content_based = self._get_content_based_recommendations(
            cursor, user_id, recent_songs, user_profile, limit // 2
        )
        recommendations.extend(content_based)
        
        # 4. Collaborative filtering (si hay suficientes datos)
        collaborative = self._get_collaborative_recommendations(
            cursor, user_id, recent_songs, limit // 3
        )
        recommendations.extend(collaborative)
        
        # 5. Discovery recommendations
        discovery = self._get_discovery_recommendations(
            cursor, user_id, user_profile, limit // 4
        )
        recommendations.extend(discovery)
        
        # 6. Eliminar duplicados y ordenar
        recommendations = self._deduplicate_and_sort(recommendations)
        
        return recommendations[:limit]
    
    def _get_user_profile(self, cursor: sqlite3.Cursor, user_id: str) -> Optional[Dict]:
        """Obtener perfil del usuario"""
        cursor.execute("SELECT * FROM user_profile WHERE user_id = ?", (user_id,))
        row = cursor.fetchone()
        
        if not row:
            return None
        
        return {
            'favorite_genres': json.loads(row['favorite_genres'] or '[]'),
            'favorite_artists': json.loads(row['favorite_artists'] or '[]'),
            'avg_session_duration': row['avg_session_duration'],
            'preferred_bpm_range': json.loads(row['preferred_bpm_range'] or '[60,140]'),
            'preferred_energy_range': json.loads(row['preferred_energy_range'] or '[0.3,0.8]'),
            'discovery_taste': row['discovery_taste']
        }
    
    def _get_recent_songs(self, cursor: sqlite3.Cursor, user_id: str, limit: int) -> List[Dict]:
        """Obtener canciones recientes del usuario"""
        cursor.execute("""
            SELECT s.*, ui.interaction_type, ui.timestamp
            FROM songs s
            JOIN user_interactions ui ON s.song_id = ui.song_id
            WHERE ui.user_id = ? AND ui.interaction_type IN ('play', 'like')
            ORDER BY ui.timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def _get_content_based_recommendations(
        self, cursor: sqlite3.Cursor, user_id: str, recent_songs: List[Dict], 
        user_profile: Optional[Dict], limit: int
    ) -> List[Recommendation]:
        """Generar recomendaciones basadas en contenido"""
        recommendations = []
        
        if not recent_songs:
            return recommendations
        
        # Analizar características de las canciones recientes
        genre_counts = Counter()
        artist_counts = Counter()
        bpm_values = []
        energy_values = []
        
        # Obtener géneros de las canciones recientes
        for song in recent_songs[:20]:  # Top 20 recientes
            cursor.execute("""
                SELECT g.name FROM genres g
                JOIN artist_genres ag ON g.genre_id = ag.genre_id
                WHERE ag.artist_id = ?
            """, (song['artist_id'],))
            
            genres = [row[0] for row in cursor.fetchall()]
            for genre in genres:
                genre_counts[genre] += 1
            
            artist_counts[song['artist_id']] += 1
            
            if song['bpm']:
                bpm_values.append(song['bpm'])
            if song['energy_level']:
                energy_values.append(song['energy_level'])
        
        # Calcular preferencias promedio
        avg_bpm = sum(bpm_values) / len(bpm_values) if bpm_values else 120
        avg_energy = sum(energy_values) / len(energy_values) if energy_values else 0.5
        
        # Encontrar canciones similares
        top_genres = [g for g, _ in genre_counts.most_common(3)]
        top_artists = [a for a, _ in artist_counts.most_common(5)]
        
        # Construir consulta SQL dinámica
        excluded_songs = [s['song_id'] for s in recent_songs]
        
        if top_genres and top_artists:
            placeholders_genres = ','.join(['?' for _ in top_genres])
            placeholders_artists = ','.join(['?' for _ in top_artists])
            placeholders_excluded = ','.join(['?' for _ in excluded_songs])
            
            sql = f"""
                SELECT DISTINCT s.*, a.name as artist_name, al.title as album_title
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                LEFT JOIN albums al ON s.album_id = al.album_id
                LEFT JOIN artist_genres ag ON s.artist_id = ag.artist_id
                LEFT JOIN genres g ON ag.genre_id = g.genre_id
                WHERE (g.name IN ({placeholders_genres}) OR s.artist_id IN ({placeholders_artists}))
                AND s.song_id NOT IN ({placeholders_excluded})
                ORDER BY s.popularity_score DESC
                LIMIT 50
            """
            
            cursor.execute(sql, top_genres + top_artists + excluded_songs)
        else:
            # Fallback: artistas similares
            if top_artists:
                placeholders_artists = ','.join(['?' for _ in top_artists])
                placeholders_excluded = ','.join(['?' for _ in excluded_songs])
                
                sql = f"""
                    SELECT s.*, a.name as artist_name, al.title as album_title
                    FROM songs s
                    JOIN artists a ON s.artist_id = a.artist_id
                    LEFT JOIN albums al ON s.album_id = al.album_id
                    WHERE s.artist_id IN ({placeholders_artists})
                    AND s.song_id NOT IN ({placeholders_excluded})
                    ORDER BY s.popularity_score DESC
                    LIMIT 50
                """
                
                cursor.execute(sql, top_artists + excluded_songs)
            else:
                return recommendations
        
        candidates = cursor.fetchall()
        
        # Calcular scores de recomendación
        for song in candidates:
            score = 0.0
            reasons = []
            
            # Score por género
            cursor.execute("""
                SELECT g.name FROM genres g
                JOIN artist_genres ag ON g.genre_id = ag.genre_id
                WHERE ag.artist_id = ?
            """, (song['artist_id'],))
            
            song_genres = [row[0] for row in cursor.fetchall()]
            genre_score = sum(genre_counts.get(g, 0) for g in song_genres) / len(recent_songs)
            score += genre_score * 0.4
            
            if genre_score > 0:
                reasons.append(f"Género favorito: {', '.join(set(song_genres) & set(top_genres))}")
            
            # Score por BPM similar
            if song['bpm']:
                bpm_diff = abs(song['bpm'] - avg_bpm)
                bpm_score = max(0, 1 - (bpm_diff / 60))  # Normalizar a 0-1
                score += bpm_score * 0.2
            
            # Score por energía similar
            if song['energy_level']:
                energy_diff = abs(song['energy_level'] - avg_energy)
                energy_score = max(0, 1 - energy_diff)
                score += energy_score * 0.2
            
            # Score por popularidad
            popularity_score = song['popularity_score'] / 100
            score += popularity_score * 0.2
            
            recommendation = Recommendation(
                song_id=song['song_id'],
                title=song['title'],
                artist=song['artist_name'],
                album=song['album_title'] or 'Unknown Album',
                thumbnail_url=song['thumbnail_url'],
                youtube_url=song['youtube_url'],
                recommendation_score=score,
                recommendation_type='content_based',
                reason=' | '.join(reasons) or 'Basado en tu gusto musical',
                artist_id=song['artist_id']
            )
            recommendations.append(recommendation)
        
        return sorted(recommendations, key=lambda x: x.recommendation_score, reverse=True)[:limit]
    
    def _get_collaborative_recommendations(
        self, cursor: sqlite3.Cursor, user_id: str, recent_songs: List[Dict], limit: int
    ) -> List[Recommendation]:
        """Recomendaciones basadas en usuarios similares (collaborative filtering)"""
        recommendations = []
        
        if len(recent_songs) < 5:
            return recommendations
        
        # Encontrar usuarios con gustos similares
        user_songs = set(s['song_id'] for s in recent_songs)
        
        cursor.execute("""
            SELECT ui.user_id, COUNT(*) as common_songs
            FROM user_interactions ui
            WHERE ui.song_id IN ({}) AND ui.user_id != ? AND ui.interaction_type = 'play'
            GROUP BY ui.user_id
            HAVING common_songs >= 2
            ORDER BY common_songs DESC
            LIMIT 10
        """.format(','.join(['?' for _ in user_songs])), list(user_songs) + [user_id])
        
        similar_users = cursor.fetchall()
        
        if not similar_users:
            return recommendations
        
        # Obtener canciones que les gustaron a usuarios similares
        similar_user_ids = [row['user_id'] for row in similar_users]
        excluded_songs = [s['song_id'] for s in recent_songs]
        
        placeholders_users = ','.join(['?' for _ in similar_user_ids])
        placeholders_excluded = ','.join(['?' for _ in excluded_songs])
        
        cursor.execute(f"""
            SELECT s.*, a.name as artist_name, al.title as album_title, COUNT(*) as recommendation_count
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            JOIN user_interactions ui ON s.song_id = ui.song_id
            WHERE ui.user_id IN ({placeholders_users})
            AND ui.song_id NOT IN ({placeholders_excluded})
            AND ui.interaction_type = 'play'
            GROUP BY s.song_id
            ORDER BY recommendation_count DESC, s.popularity_score DESC
            LIMIT 30
        """, similar_user_ids + excluded_songs)
        
        candidates = cursor.fetchall()
        
        for song in candidates:
            score = (song['recommendation_count'] / len(similar_users)) * 0.7 + (song['popularity_score'] / 100) * 0.3
            
            recommendation = Recommendation(
                song_id=song['song_id'],
                title=song['title'],
                artist=song['artist_name'],
                album=song['album_title'] or 'Unknown Album',
                thumbnail_url=song['thumbnail_url'],
                youtube_url=song['youtube_url'],
                recommendation_score=score,
                recommendation_type='collaborative',
                reason=f'Popular entre usuarios con gustos similares',
                artist_id=song['artist_id']
            )
            recommendations.append(recommendation)
        
        return sorted(recommendations, key=lambda x: x.recommendation_score, reverse=True)[:limit]
    
    def _get_discovery_recommendations(
        self, cursor: sqlite3.Cursor, user_id: str, user_profile: Optional[Dict], limit: int
    ) -> List[Recommendation]:
        """Recomendaciones para descubrir nueva música"""
        recommendations = []
        
        if not user_profile:
            return recommendations
        
        discovery_taste = user_profile.get('discovery_taste', 0.5)
        favorite_genres = user_profile.get('favorite_genres', [])
        
        # Encontrar géneros relacionados pero no explorados
        cursor.execute("""
            SELECT DISTINCT g1.name as genre_name, COUNT(*) as song_count
            FROM genres g1
            JOIN genres g2 ON g1.parent_genre_id = g2.parent_genre_id
            JOIN artist_genres ag ON g1.genre_id = ag.genre_id
            JOIN songs s ON ag.artist_id = s.artist_id
            WHERE g2.name IN ({})
            AND g1.name NOT IN ({})
            GROUP BY g1.name
            HAVING song_count >= 5
            ORDER BY song_count DESC
            LIMIT 5
        """.format(
            ','.join(['?' for _ in favorite_genres]),
            ','.join(['?' for _ in favorite_genres])
        ), favorite_genres + favorite_genres)
        
        related_genres = cursor.fetchall()
        
        if not related_genres:
            return recommendations
        
        # Obtener canciones de géneros relacionados
        genre_names = [row['genre_name'] for row in related_genres]
        placeholders_genres = ','.join(['?' for _ in genre_names])
        
        cursor.execute(f"""
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            JOIN artist_genres ag ON s.artist_id = ag.artist_id
            JOIN genres g ON ag.genre_id = g.genre_id
            WHERE g.name IN ({placeholders_genres})
            ORDER BY s.popularity_score DESC
            LIMIT 30
        """, genre_names)
        
        candidates = cursor.fetchall()
        
        for song in candidates:
            # Score basado en popularidad y factor de descubrimiento
            base_score = song['popularity_score'] / 100
            discovery_bonus = discovery_taste * 0.3
            score = base_score * (1 - discovery_bonus) + discovery_bonus
            
            recommendation = Recommendation(
                song_id=song['song_id'],
                title=song['title'],
                artist=song['artist_name'],
                album=song['album_title'] or 'Unknown Album',
                thumbnail_url=song['thumbnail_url'],
                youtube_url=song['youtube_url'],
                recommendation_score=score,
                recommendation_type='discovery',
                reason=f'Descubre: {genre_names[0] if genre_names else "nueva música"}',
                artist_id=song['artist_id']
            )
            recommendations.append(recommendation)
        
        return sorted(recommendations, key=lambda x: x.recommendation_score, reverse=True)[:limit]
    
    def _get_trending_recommendations(self, cursor: sqlite3.Cursor, limit: int) -> List[Recommendation]:
        """Recomendaciones de canciones populares para nuevos usuarios"""
        cursor.execute("""
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            WHERE s.popularity_score > 70
            ORDER BY s.popularity_score DESC, s.play_count DESC
            LIMIT ?
        """, (limit,))
        
        recommendations = []
        
        for song in cursor.fetchall():
            recommendation = Recommendation(
                song_id=song['song_id'],
                title=song['title'],
                artist=song['artist_name'],
                album=song['album_title'] or 'Unknown Album',
                thumbnail_url=song['thumbnail_url'],
                youtube_url=song['youtube_url'],
                recommendation_score=song['popularity_score'] / 100,
                recommendation_type='trending',
                reason='Popular en la app',
                artist_id=song['artist_id']
            )
            recommendations.append(recommendation)
        
        return recommendations
    
    def _deduplicate_and_sort(self, recommendations: List[Recommendation]) -> List[Recommendation]:
        """Eliminar duplicados y ordenar por score"""
        seen_songs = set()
        unique_recommendations = []
        
        for rec in recommendations:
            if rec.song_id not in seen_songs:
                seen_songs.add(rec.song_id)
                unique_recommendations.append(rec)
        
        return sorted(unique_recommendations, key=lambda x: x.recommendation_score, reverse=True)
    
    def get_next_recommendations(self, user_id: str, current_song_id: int, limit: int = 5) -> List[Recommendation]:
        """
        Obtener siguientes canciones recomendadas (para cola de reproducción)
        
        Args:
            user_id: ID del usuario
            current_song_id: ID de la canción actual
            limit: Número de siguientes canciones
        
        Returns:
            Lista de siguientes canciones recomendadas
        """
        cursor = self.conn.cursor()
        
        # 1. Obtener características de la canción actual
        cursor.execute("""
            SELECT s.*, a.name as artist_name
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            WHERE s.song_id = ?
        """, (current_song_id,))
        
        current_song = cursor.fetchone()
        
        if not current_song:
            return []
        
        recommendations = []
        
        # 2. Canciones del mismo artista (prioridad alta)
        cursor.execute("""
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            WHERE s.artist_id = ? AND s.song_id != ?
            ORDER BY s.popularity_score DESC
            LIMIT 3
        """, (current_song['artist_id'], current_song_id))
        
        for song in cursor.fetchall():
            recommendation = Recommendation(
                song_id=song['song_id'],
                title=song['title'],
                artist=song['artist_name'],
                album=song['album_title'] or 'Unknown Album',
                thumbnail_url=song['thumbnail_url'],
                youtube_url=song['youtube_url'],
                recommendation_score=0.9,
                recommendation_type='same_artist',
                reason='Más del mismo artista',
                artist_id=song['artist_id']
            )
            recommendations.append(recommendation)
        
        # 3. Canciones con BPM y energía similares
        if current_song['bpm'] or current_song['energy_level']:
            bpm_condition = ""
            energy_condition = ""
            params = [current_song_id]
            
            if current_song['bpm']:
                bpm_condition = "AND ABS(s.bpm - ?) <= 15"
                params.append(current_song['bpm'])
            
            if current_song['energy_level']:
                energy_condition = "AND ABS(s.energy_level - ?) <= 0.2"
                params.append(current_song['energy_level'])
            
            sql = f"""
                SELECT s.*, a.name as artist_name, al.title as album_title
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                LEFT JOIN albums al ON s.album_id = al.album_id
                WHERE s.song_id != ? {bpm_condition} {energy_condition}
                ORDER BY s.popularity_score DESC
                LIMIT 5
            """
            
            cursor.execute(sql, params)
            
            for song in cursor.fetchall():
                recommendation = Recommendation(
                    song_id=song['song_id'],
                    title=song['title'],
                    artist=song['artist_name'],
                    album=song['album_title'] or 'Unknown Album',
                    thumbnail_url=song['thumbnail_url'],
                    youtube_url=song['youtube_url'],
                    recommendation_score=0.7,
                    recommendation_type='similar_energy',
                    reason='Energía y ritmo similares',
                    artist_id=song['artist_id']
                )
                recommendations.append(recommendation)
        
        # 4. Completar con recomendaciones personalizadas si es necesario
        if len(recommendations) < limit:
            additional_recs = self.get_recommendations(user_id, limit - len(recommendations), 'player')
            recommendations.extend(additional_recs)
        
        return recommendations[:limit]
    
    def update_user_profile(self, user_id: str, song_id: int, interaction_type: str):
        """Actualizar perfil de usuario basado en interacciones"""
        cursor = self.conn.cursor()
        
        # Obtener información de la canción
        cursor.execute("""
            SELECT s.*, a.name as artist_name
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            WHERE s.song_id = ?
        """, (song_id,))
        
        song = cursor.fetchone()
        
        if not song:
            return
        
        # Obtener perfil actual
        cursor.execute("SELECT * FROM user_profile WHERE user_id = ?", (user_id,))
        profile = cursor.fetchone()
        
        if not profile:
            # Crear nuevo perfil
            cursor.execute("""
                INSERT INTO user_profile (user_id, favorite_genres, favorite_artists, last_updated)
                VALUES (?, ?, ?, datetime('now'))
            """, (user_id, '[]', '[]'))
            
            favorite_genres = []
            favorite_artists = []
            preferred_bpm_range = [60, 140]
            preferred_energy_range = [0.3, 0.8]
            discovery_taste = 0.5
        else:
            favorite_genres = json.loads(profile['favorite_genres'] or '[]')
            favorite_artists = json.loads(profile['favorite_artists'] or '[]')
            preferred_bpm_range = json.loads(profile['preferred_bpm_range'] or '[60,140]')
            preferred_energy_range = json.loads(profile['preferred_energy_range'] or '[0.3,0.8]')
            discovery_taste = profile['discovery_taste']
        
        # Actualizar favoritos basados en interacción
        if interaction_type in ['play', 'like']:
            # Agregar artista a favoritos
            if song['artist_id'] not in favorite_artists:
                favorite_artists.append(song['artist_id'])
                # Limitar a 50 artistas favoritos
                favorite_artists = favorite_artists[-50:]
            
            # Actualizar géneros favoritos
            cursor.execute("""
                SELECT g.name FROM genres g
                JOIN artist_genres ag ON g.genre_id = ag.genre_id
                WHERE ag.artist_id = ?
            """, (song['artist_id'],))
            
            song_genres = [row[0] for row in cursor.fetchall()]
            for genre in song_genres:
                if genre not in favorite_genres:
                    favorite_genres.append(genre)
                    # Limitar a 20 géneros favoritos
                    favorite_genres = favorite_genres[-20:]
            
            # Actualizar rangos preferidos
            if song['bpm']:
                preferred_bpm_range[0] = min(preferred_bpm_range[0], song['bpm'] - 10)
                preferred_bpm_range[1] = max(preferred_bpm_range[1], song['bpm'] + 10)
            
            if song['energy_level']:
                preferred_energy_range[0] = min(preferred_energy_range[0], song['energy_level'] - 0.1)
                preferred_energy_range[1] = max(preferred_energy_range[1], song['energy_level'] + 0.1)
        
        # Guardar perfil actualizado
        cursor.execute("""
            UPDATE user_profile 
            SET favorite_genres = ?, favorite_artists = ?, 
                preferred_bpm_range = ?, preferred_energy_range = ?,
                last_updated = datetime('now')
            WHERE user_id = ?
        """, (
            json.dumps(favorite_genres),
            json.dumps(favorite_artists),
            json.dumps(preferred_bpm_range),
            json.dumps(preferred_energy_range),
            user_id
        ))
        
        self.conn.commit()
    
    def close(self):
        """Cerrar conexión a base de datos"""
        if self.conn:
            self.conn.close()
