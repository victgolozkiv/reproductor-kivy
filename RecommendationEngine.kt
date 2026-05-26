package com.musicplayer.recommendation

import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import java.util.*
import kotlin.math.abs

/**
 * Motor de Recomendaciones Avanzado para Reproductor de Música
 * Implementa Content-Based Filtering, Collaborative Filtering y User Profiling
 */
class RecommendationEngine private constructor(private val context: Context) {
    
    private val database: SQLiteDatabase by lazy { MusicDatabase.getInstance(context) }
    private val recommendationScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val recommendationCache = LRUCache<String, List<Recommendation>>(50)
    
    data class Recommendation(
        val songId: Long,
        val title: String,
        val artist: String,
        val album: String,
        val thumbnailUrl: String,
        val youtubeUrl: String,
        val recommendationScore: Float,
        val recommendationType: RecommendationType,
        val reason: String,
        val artistId: Long
    )
    
    enum class RecommendationType {
        CONTENT_BASED, COLLABORATIVE, TRENDING, DISCOVERY, SAME_ARTIST, SIMILAR_ENERGY
    }
    
    companion object {
        @Volatile
        private var INSTANCE: RecommendationEngine? = null
        
        fun getInstance(context: Context): RecommendationEngine {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: RecommendationEngine(context.applicationContext).also { INSTANCE = it }
            }
        }
    }
    
    /**
     * Obtener recomendaciones personalizadas para un usuario
     */
    suspend fun getRecommendations(
        userId: String,
        limit: Int = 20,
        context: RecommendationContext = RecommendationContext.GENERAL
    ): List<Recommendation> = withContext(Dispatchers.IO) {
        val cacheKey = "${userId}_${limit}_${context.name}"
        
        // Verificar caché
        recommendationCache.get(cacheKey)?.let { return@withContext it }
        
        // Obtener perfil del usuario
        val userProfile = getUserProfile(userId)
        
        // Obtener historial reciente
        val recentSongs = getRecentSongs(userId, 50)
        
        val recommendations = mutableListOf<Recommendation>()
        
        if (recentSongs.isEmpty() && userProfile == null) {
            // Nuevo usuario - recomendaciones populares
            val trendingRecommendations = getTrendingRecommendations(limit)
            recommendations.addAll(trendingRecommendations)
        } else {
            // 1. Content-based recommendations (50%)
            val contentBased = getContentBasedRecommendations(userId, recentSongs, userProfile, limit / 2)
            recommendations.addAll(contentBased)
            
            // 2. Collaborative filtering (30%)
            val collaborative = getCollaborativeRecommendations(userId, recentSongs, limit / 3)
            recommendations.addAll(collaborative)
            
            // 3. Discovery recommendations (20%)
            val discovery = getDiscoveryRecommendations(userId, userProfile, limit / 4)
            recommendations.addAll(discovery)
        }
        
        // Eliminar duplicados y ordenar
        val finalRecommendations = deduplicateAndSort(recommendations).take(limit)
        
        // Guardar en caché
        recommendationCache.put(cacheKey, finalRecommendations)
        
        finalRecommendations
    }
    
    /**
     * Obtener siguientes canciones recomendadas (para cola de reproducción)
     */
    suspend fun getNextRecommendations(
        userId: String,
        currentSongId: Long,
        limit: Int = 5
    ): List<Recommendation> = withContext(Dispatchers.IO) {
        val recommendations = mutableListOf<Recommendation>()
        
        // Obtener características de la canción actual
        val currentSong = getCurrentSongDetails(currentSongId) ?: return@withContext emptyList()
        
        // 1. Canciones del mismo artista (prioridad alta)
        val sameArtistSongs = getSameArtistSongs(currentSong.artistId, currentSongId, 3)
        recommendations.addAll(sameArtistSongs)
        
        // 2. Canciones con BPM y energía similares
        val similarEnergySongs = getSimilarEnergySongs(currentSong, 5)
        recommendations.addAll(similarEnergySongs)
        
        // 3. Completar con recomendaciones personalizadas
        if (recommendations.size < limit) {
            val additionalRecs = getRecommendations(userId, limit - recommendations.size, RecommendationContext.PLAYER)
            recommendations.addAll(additionalRecs)
        }
        
        recommendations.take(limit)
    }
    
    /**
     * Obtener perfil del usuario
     */
    private suspend fun getUserProfile(userId: String): UserProfile? = withContext(Dispatchers.IO) {
        val cursor = database.rawQuery(
            "SELECT * FROM user_profile WHERE user_id = ?",
            arrayOf(userId)
        )
        
        cursor.use { c ->
            if (c.moveToFirst()) {
                UserProfile(
                    favoriteGenres = parseJsonArray(c.getString(c.getColumnIndexOrThrow("favorite_genres"))),
                    favoriteArtists = parseJsonLongArray(c.getString(c.getColumnIndexOrThrow("favorite_artists"))),
                    avgSessionDuration = c.getDouble(c.getColumnIndexOrThrow("avg_session_duration")),
                    preferredBpmRange = parseJsonIntArray(c.getString(c.getColumnIndexOrThrow("preferred_bpm_range"))),
                    preferredEnergyRange = parseJsonDoubleArray(c.getString(c.getColumnIndexOrThrow("preferred_energy_range"))),
                    discoveryTaste = c.getFloat(c.getColumnIndexOrThrow("discovery_taste"))
                )
            } else null
        }
    }
    
    /**
     * Obtener canciones recientes del usuario
     */
    private suspend fun getRecentSongs(userId: String, limit: Int): List<SongInteraction> = withContext(Dispatchers.IO) {
        val cursor = database.rawQuery(
            """
            SELECT s.*, ui.interaction_type, ui.timestamp
            FROM songs s
            JOIN user_interactions ui ON s.song_id = ui.song_id
            WHERE ui.user_id = ? AND ui.interaction_type IN ('play', 'like')
            ORDER BY ui.timestamp DESC
            LIMIT ?
            """.trimIndent(),
            arrayOf(userId, limit.toString())
        )
        
        val interactions = mutableListOf<SongInteraction>()
        
        cursor.use { c ->
            while (c.moveToNext()) {
                interactions.add(
                    SongInteraction(
                        songId = c.getLong(c.getColumnIndexOrThrow("song_id")),
                        title = c.getString(c.getColumnIndexOrThrow("title")),
                        artistId = c.getLong(c.getColumnIndexOrThrow("artist_id")),
                        bpm = c.getInt(c.getColumnIndexOrThrow("bpm")).takeIf { it > 0 },
                        energyLevel = c.getFloat(c.getColumnIndexOrThrow("energy_level")).takeIf { it > 0f },
                        interactionType = c.getString(c.getColumnIndexOrThrow("interaction_type")),
                        timestamp = c.getString(c.getColumnIndexOrThrow("timestamp"))
                    )
                )
            }
        }
        
        interactions
    }
    
    /**
     * Content-based recommendations
     */
    private suspend fun getContentBasedRecommendations(
        userId: String,
        recentSongs: List<SongInteraction>,
        userProfile: UserProfile?,
        limit: Int
    ): List<Recommendation> = withContext(Dispatchers.IO) {
        if (recentSongs.isEmpty()) return@withContext emptyList()
        
        val recommendations = mutableListOf<Recommendation>()
        
        // Analizar características de las canciones recientes
        val genreCounts = mutableMapOf<String, Int>()
        val artistCounts = mutableMapOf<Long, Int>()
        val bpmValues = mutableListOf<Int>()
        val energyValues = mutableListOf<Float>()
        
        // Obtener géneros y contar preferencias
        recentSongs.take(20).forEach { song ->
            // Obtener géneros del artista
            val genreCursor = database.rawQuery(
                """
                SELECT g.name FROM genres g
                JOIN artist_genres ag ON g.genre_id = ag.genre_id
                WHERE ag.artist_id = ?
                """.trimIndent(),
                arrayOf(song.artistId.toString())
            )
            
            genreCursor.use { c ->
                while (c.moveToNext()) {
                    val genre = c.getString(0)
                    genreCounts[genre] = genreCounts.getOrDefault(genre, 0) + 1
                }
            }
            
            artistCounts[song.artistId] = artistCounts.getOrDefault(song.artistId, 0) + 1
            
            song.bpm?.let { bpmValues.add(it) }
            song.energyLevel?.let { energyValues.add(it) }
        }
        
        // Calcular preferencias promedio
        val avgBpm = if (bpmValues.isNotEmpty()) bpmValues.average().toInt() else 120
        val avgEnergy = if (energyValues.isNotEmpty()) energyValues.average() else 0.5f
        
        // Encontrar géneros y artistas principales
        val topGenres = genreCounts.entries.sortedByDescending { it.value }.take(3).map { it.key }
        val topArtists = artistCounts.entries.sortedByDescending { it.value }.take(5).map { it.key }
        
        // Buscar canciones similares
        val excludedSongIds = recentSongs.map { it.songId }
        
        val candidates = if (topGenres.isNotEmpty() && topArtists.isNotEmpty()) {
            findSimilarSongs(topGenres, topArtists, excludedSongIds, 50)
        } else if (topArtists.isNotEmpty()) {
            findSongsByArtists(topArtists, excludedSongIds, 50)
        } else {
            emptyList()
        }
        
        // Calcular scores de recomendación
        candidates.forEach { song ->
            var score = 0f
            val reasons = mutableListOf<String>()
            
            // Score por género
            val songGenres = getSongGenres(song.artistId)
            val genreScore = songGenres.sumOf { genreCounts.getOrDefault(it, 0) }.toFloat() / recentSongs.size
            score += genreScore * 0.4f
            
            if (genreScore > 0) {
                val matchingGenres = songGenres.intersect(topGenres.toSet())
                if (matchingGenres.isNotEmpty()) {
                    reasons.add("Género favorito: ${matchingGenres.joinToString()}")
                }
            }
            
            // Score por BPM similar
            song.bpm?.let { bpm ->
                val bpmDiff = abs(bpm - avgBpm)
                val bpmScore = max(0f, 1f - (bpmDiff / 60f))
                score += bpmScore * 0.2f
            }
            
            // Score por energía similar
            song.energyLevel?.let { energy ->
                val energyDiff = abs(energy - avgEnergy)
                val energyScore = max(0f, 1f - energyDiff)
                score += energyScore * 0.2f
            }
            
            // Score por popularidad
            score += song.popularityScore / 100f * 0.2f
            
            recommendations.add(
                Recommendation(
                    songId = song.songId,
                    title = song.title,
                    artist = song.artist,
                    album = song.album,
                    thumbnailUrl = song.thumbnailUrl,
                    youtubeUrl = song.youtubeUrl,
                    recommendationScore = score,
                    recommendationType = RecommendationType.CONTENT_BASED,
                    reason = reasons.joinToString(" | ") ?: "Basado en tu gusto musical",
                    artistId = song.artistId
                )
            )
        }
        
        recommendations.sortedByDescending { it.recommendationScore }.take(limit)
    }
    
    /**
     * Collaborative filtering recommendations
     */
    private suspend fun getCollaborativeRecommendations(
        userId: String,
        recentSongs: List<SongInteraction>,
        limit: Int
    ): List<Recommendation> = withContext(Dispatchers.IO) {
        if (recentSongs.size < 5) return@withContext emptyList()
        
        val recommendations = mutableListOf<Recommendation>()
        
        // Encontrar usuarios con gustos similares
        val userSongIds = recentSongs.map { it.songId }.toSet()
        
        val similarUsersCursor = database.rawQuery(
            """
            SELECT ui.user_id, COUNT(*) as common_songs
            FROM user_interactions ui
            WHERE ui.song_id IN (${userSongIds.joinToString(",")}) 
            AND ui.user_id != ? 
            AND ui.interaction_type = 'play'
            GROUP BY ui.user_id
            HAVING common_songs >= 2
            ORDER BY common_songs DESC
            LIMIT 10
            """.trimIndent(),
            arrayOf(userId)
        )
        
        val similarUsers = mutableListOf<Pair<String, Int>>()
        similarUsersCursor.use { c ->
            while (c.moveToNext()) {
                similarUsers.add(
                    c.getString(0) to c.getInt(1)
                )
            }
        }
        
        if (similarUsers.isEmpty()) return@withContext emptyList()
        
        // Obtener canciones que les gustaron a usuarios similares
        val similarUserIds = similarUsers.map { it.first }
        val excludedSongIds = recentSongs.map { it.songId }
        
        val candidatesCursor = database.rawQuery(
            """
            SELECT s.*, a.name as artist_name, al.title as album_title, COUNT(*) as recommendation_count
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            JOIN user_interactions ui ON s.song_id = ui.song_id
            WHERE ui.user_id IN (${similarUserIds.joinToString(",")})
            AND ui.song_id NOT IN (${excludedSongIds.joinToString(",")})
            AND ui.interaction_type = 'play'
            GROUP BY s.song_id
            ORDER BY recommendation_count DESC, s.popularity_score DESC
            LIMIT 30
            """.trimIndent(),
            null
        )
        
        candidatesCursor.use { c ->
            while (c.moveToNext()) {
                val recommendationCount = c.getInt(c.getColumnIndexOrThrow("recommendation_count"))
                val popularityScore = c.getFloat(c.getColumnIndexOrThrow("popularity_score"))
                
                val score = (recommendationCount.toFloat() / similarUsers.size) * 0.7f + (popularityScore / 100f) * 0.3f
                
                recommendations.add(
                    Recommendation(
                        songId = c.getLong(c.getColumnIndexOrThrow("song_id")),
                        title = c.getString(c.getColumnIndexOrThrow("title")),
                        artist = c.getString(c.getColumnIndexOrThrow("artist_name")),
                        album = c.getString(c.getColumnIndexOrThrow("album_title")) ?: "Unknown Album",
                        thumbnailUrl = c.getString(c.getColumnIndexOrThrow("thumbnail_url")) ?: "",
                        youtubeUrl = c.getString(c.getColumnIndexOrThrow("youtube_url")) ?: "",
                        recommendationScore = score,
                        recommendationType = RecommendationType.COLLABORATIVE,
                        reason = "Popular entre usuarios con gustos similares",
                        artistId = c.getLong(c.getColumnIndexOrThrow("artist_id"))
                    )
                )
            }
        }
        
        recommendations.sortedByDescending { it.recommendationScore }.take(limit)
    }
    
    /**
     * Discovery recommendations
     */
    private suspend fun getDiscoveryRecommendations(
        userId: String,
        userProfile: UserProfile?,
        limit: Int
    ): List<Recommendation> = withContext(Dispatchers.IO) {
        if (userProfile == null) return@withContext emptyList()
        
        val recommendations = mutableListOf<Recommendation>()
        val favoriteGenres = userProfile.favoriteGenres
        
        if (favoriteGenres.isEmpty()) return@withContext emptyList()
        
        // Encontrar géneros relacionados pero no explorados
        val relatedGenresCursor = database.rawQuery(
            """
            SELECT DISTINCT g1.name as genre_name, COUNT(*) as song_count
            FROM genres g1
            JOIN genres g2 ON g1.parent_genre_id = g2.parent_genre_id
            JOIN artist_genres ag ON g1.genre_id = ag.genre_id
            JOIN songs s ON ag.artist_id = s.artist_id
            WHERE g2.name IN (${favoriteGenres.joinToString(",")})
            AND g1.name NOT IN (${favoriteGenres.joinToString(",")})
            GROUP BY g1.name
            HAVING song_count >= 5
            ORDER BY song_count DESC
            LIMIT 5
            """.trimIndent(),
            null
        )
        
        val relatedGenres = mutableListOf<String>()
        relatedGenresCursor.use { c ->
            while (c.moveToNext()) {
                relatedGenres.add(c.getString(c.getColumnIndexOrThrow("genre_name")))
            }
        }
        
        if (relatedGenres.isEmpty()) return@withContext emptyList()
        
        // Obtener canciones de géneros relacionados
        val candidatesCursor = database.rawQuery(
            """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            JOIN artist_genres ag ON s.artist_id = ag.genre_id
            JOIN genres g ON ag.genre_id = g.genre_id
            WHERE g.name IN (${relatedGenres.joinToString(",")})
            ORDER BY s.popularity_score DESC
            LIMIT 30
            """.trimIndent(),
            null
        )
        
        candidatesCursor.use { c ->
            while (c.moveToNext()) {
                val baseScore = c.getFloat(c.getColumnIndexOrThrow("popularity_score")) / 100f
                val discoveryBonus = userProfile.discoveryTaste * 0.3f
                val score = baseScore * (1 - discoveryBonus) + discoveryBonus
                
                recommendations.add(
                    Recommendation(
                        songId = c.getLong(c.getColumnIndexOrThrow("song_id")),
                        title = c.getString(c.getColumnIndexOrThrow("title")),
                        artist = c.getString(c.getColumnIndexOrThrow("artist_name")),
                        album = c.getString(c.getColumnIndexOrThrow("album_title")) ?: "Unknown Album",
                        thumbnailUrl = c.getString(c.getColumnIndexOrThrow("thumbnail_url")) ?: "",
                        youtubeUrl = c.getString(c.getColumnIndexOrThrow("youtube_url")) ?: "",
                        recommendationScore = score,
                        recommendationType = RecommendationType.DISCOVERY,
                        reason = "Descubre: ${relatedGenres.firstOrNull() ?: "nueva música"}",
                        artistId = c.getLong(c.getColumnIndexOrThrow("artist_id"))
                    )
                )
            }
        }
        
        recommendations.sortedByDescending { it.recommendationScore }.take(limit)
    }
    
    /**
     * Trending recommendations para nuevos usuarios
     */
    private suspend fun getTrendingRecommendations(limit: Int): List<Recommendation> = withContext(Dispatchers.IO) {
        val cursor = database.rawQuery(
            """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            WHERE s.popularity_score > 70
            ORDER BY s.popularity_score DESC, s.play_count DESC
            LIMIT ?
            """.trimIndent(),
            arrayOf(limit.toString())
        )
        
        val recommendations = mutableListOf<Recommendation>()
        
        cursor.use { c ->
            while (c.moveToNext()) {
                recommendations.add(
                    Recommendation(
                        songId = c.getLong(c.getColumnIndexOrThrow("song_id")),
                        title = c.getString(c.getColumnIndexOrThrow("title")),
                        artist = c.getString(c.getColumnIndexOrThrow("artist_name")),
                        album = c.getString(c.getColumnIndexOrThrow("album_title")) ?: "Unknown Album",
                        thumbnailUrl = c.getString(c.getColumnIndexOrThrow("thumbnail_url")) ?: "",
                        youtubeUrl = c.getString(c.getColumnIndexOrThrow("youtube_url")) ?: "",
                        recommendationScore = c.getFloat(c.getColumnIndexOrThrow("popularity_score")) / 100f,
                        recommendationType = RecommendationType.TRENDING,
                        reason = "Popular en la app",
                        artistId = c.getLong(c.getColumnIndexOrThrow("artist_id"))
                    )
                )
            }
        }
        
        recommendations
    }
    
    /**
     * Obtener canciones del mismo artista
     */
    private suspend fun getSameArtistSongs(artistId: Long, excludeSongId: Long, limit: Int): List<Recommendation> = withContext(Dispatchers.IO) {
        val cursor = database.rawQuery(
            """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            WHERE s.artist_id = ? AND s.song_id != ?
            ORDER BY s.popularity_score DESC
            LIMIT ?
            """.trimIndent(),
            arrayOf(artistId.toString(), excludeSongId.toString(), limit.toString())
        )
        
        val recommendations = mutableListOf<Recommendation>()
        
        cursor.use { c ->
            while (c.moveToNext()) {
                recommendations.add(
                    Recommendation(
                        songId = c.getLong(c.getColumnIndexOrThrow("song_id")),
                        title = c.getString(c.getColumnIndexOrThrow("title")),
                        artist = c.getString(c.getColumnIndexOrThrow("artist_name")),
                        album = c.getString(c.getColumnIndexOrThrow("album_title")) ?: "Unknown Album",
                        thumbnailUrl = c.getString(c.getColumnIndexOrThrow("thumbnail_url")) ?: "",
                        youtubeUrl = c.getString(c.getColumnIndexOrThrow("youtube_url")) ?: "",
                        recommendationScore = 0.9f,
                        recommendationType = RecommendationType.SAME_ARTIST,
                        reason = "Más del mismo artista",
                        artistId = c.getLong(c.getColumnIndexOrThrow("artist_id"))
                    )
                )
            }
        }
        
        recommendations
    }
    
    /**
     * Obtener canciones con energía similar
     */
    private suspend fun getSimilarEnergySongs(currentSong: SongDetails, limit: Int): List<Recommendation> = withContext(Dispatchers.IO) {
        if (currentSong.bpm == null && currentSong.energyLevel == null) {
            return@withContext emptyList()
        }
        
        var sql = """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            WHERE s.song_id != ?
            """.trimIndent()
        
        val params = mutableListOf(currentSong.songId.toString())
        
        currentSong.bpm?.let { bpm ->
            sql += "AND ABS(s.bpm - ?) <= 15 "
            params.add(bpm.toString())
        }
        
        currentSong.energyLevel?.let { energy ->
            sql += "AND ABS(s.energy_level - ?) <= 0.2 "
            params.add(energy.toString())
        }
        
        sql += "ORDER BY s.popularity_score DESC LIMIT ?"
        params.add(limit.toString())
        
        val cursor = database.rawQuery(sql, params.toTypedArray())
        
        val recommendations = mutableListOf<Recommendation>()
        
        cursor.use { c ->
            while (c.moveToNext()) {
                recommendations.add(
                    Recommendation(
                        songId = c.getLong(c.getColumnIndexOrThrow("song_id")),
                        title = c.getString(c.getColumnIndexOrThrow("title")),
                        artist = c.getString(c.getColumnIndexOrThrow("artist_name")),
                        album = c.getString(c.getColumnIndexOrThrow("album_title")) ?: "Unknown Album",
                        thumbnailUrl = c.getString(c.getColumnIndexOrThrow("thumbnail_url")) ?: "",
                        youtubeUrl = c.getString(c.getColumnIndexOrThrow("youtube_url")) ?: "",
                        recommendationScore = 0.7f,
                        recommendationType = RecommendationType.SIMILAR_ENERGY,
                        reason = "Energía y ritmo similares",
                        artistId = c.getLong(c.getColumnIndexOrThrow("artist_id"))
                    )
                )
            }
        }
        
        recommendations
    }
    
    /**
     * Actualizar perfil de usuario basado en interacciones
     */
    suspend fun updateUserProfile(userId: String, songId: Long, interactionType: String) = withContext(Dispatchers.IO) {
        // Obtener información de la canción
        val song = getCurrentSongDetails(songId) ?: return@withContext
        
        // Obtener perfil actual
        val currentProfile = getUserProfile(userId) ?: UserProfile()
        
        val updatedProfile = currentProfile.copy().apply {
            // Actualizar favoritos basados en interacción
            if (interactionType in listOf("play", "like")) {
                // Agregar artista a favoritos
                if (song.artistId !in favoriteArtists) {
                    favoriteArtists.add(song.artistId)
                    // Limitar a 50 artistas favoritos
                    if (favoriteArtists.size > 50) {
                        favoriteArtists.removeAt(0)
                    }
                }
                
                // Actualizar géneros favoritos
                val songGenres = getSongGenres(song.artistId)
                songGenres.forEach { genre ->
                    if (genre !in favoriteGenres) {
                        favoriteGenres.add(genre)
                        // Limitar a 20 géneros favoritos
                        if (favoriteGenres.size > 20) {
                            favoriteGenres.removeAt(0)
                        }
                    }
                }
                
                // Actualizar rangos preferidos
                song.bpm?.let { bpm ->
                    preferredBpmRange[0] = min(preferredBpmRange[0], bpm - 10)
                    preferredBpmRange[1] = max(preferredBpmRange[1], bpm + 10)
                }
                
                song.energyLevel?.let { energy ->
                    preferredEnergyRange[0] = min(preferredEnergyRange[0], energy - 0.1f)
                    preferredEnergyRange[1] = max(preferredEnergyRange[1], energy + 0.1f)
                }
            }
        }
        
        // Guardar perfil actualizado
        saveUserProfile(userId, updatedProfile)
    }
    
    // Funciones helper
    
    private fun getCurrentSongDetails(songId: Long): SongDetails? {
        val cursor = database.rawQuery(
            """
            SELECT s.*, a.name as artist_name
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            WHERE s.song_id = ?
            """.trimIndent(),
            arrayOf(songId.toString())
        )
        
        return cursor.use { c ->
            if (c.moveToFirst()) {
                SongDetails(
                    songId = c.getLong(c.getColumnIndexOrThrow("song_id")),
                    title = c.getString(c.getColumnIndexOrThrow("title")),
                    artist = c.getString(c.getColumnIndexOrThrow("artist_name")),
                    artistId = c.getLong(c.getColumnIndexOrThrow("artist_id")),
                    bpm = c.getInt(c.getColumnIndexOrThrow("bpm")).takeIf { it > 0 },
                    energyLevel = c.getFloat(c.getColumnIndexOrThrow("energy_level")).takeIf { it > 0f },
                    popularityScore = c.getFloat(c.getColumnIndexOrThrow("popularity_score")),
                    album = c.getString(c.getColumnIndexOrThrow("album_title")) ?: "Unknown Album",
                    thumbnailUrl = c.getString(c.getColumnIndexOrThrow("thumbnail_url")) ?: "",
                    youtubeUrl = c.getString(c.getColumnIndexOrThrow("youtube_url")) ?: ""
                )
            } else null
        }
    }
    
    private fun getSongGenres(artistId: Long): List<String> {
        val cursor = database.rawQuery(
            """
            SELECT g.name FROM genres g
            JOIN artist_genres ag ON g.genre_id = ag.genre_id
            WHERE ag.artist_id = ?
            """.trimIndent(),
            arrayOf(artistId.toString())
        )
        
        return cursor.use { c ->
            val genres = mutableListOf<String>()
            while (c.moveToNext()) {
                genres.add(c.getString(0))
            }
            genres
        }
    }
    
    private fun findSimilarSongs(genres: List<String>, artists: List<Long>, excludeIds: List<Long>, limit: Int): List<SongDetails> {
        // Implementación simplificada - en producción usaría consultas más optimizadas
        return emptyList()
    }
    
    private fun findSongsByArtists(artists: List<Long>, excludeIds: List<Long>, limit: Int): List<SongDetails> {
        // Implementación simplificada - en producción usaría consultas más optimizadas
        return emptyList()
    }
    
    private fun deduplicateAndSort(recommendations: List<Recommendation>): List<Recommendation> {
        val seenSongs = mutableSetOf<Long>()
        val uniqueRecommendations = mutableListOf<Recommendation>()
        
        recommendations.forEach { rec ->
            if (rec.songId !in seenSongs) {
                seenSongs.add(rec.songId)
                uniqueRecommendations.add(rec)
            }
        }
        
        return uniqueRecommendations.sortedByDescending { it.recommendationScore }
    }
    
    private fun parseJsonArray(json: String?): List<String> {
        if (json.isNullOrEmpty()) return emptyList()
        return try {
            val array = JSONArray(json)
            (0 until array.length()).map { array.getString(it) }
        } catch (e: Exception) {
            emptyList()
        }
    }
    
    private fun parseJsonLongArray(json: String?): List<Long> {
        if (json.isNullOrEmpty()) return emptyList()
        return try {
            val array = JSONArray(json)
            (0 until array.length()).map { array.getLong(it) }
        } catch (e: Exception) {
            emptyList()
        }
    }
    
    private fun parseJsonIntArray(json: String?): List<Int> {
        if (json.isNullOrEmpty()) return listOf(60, 140)
        return try {
            val array = JSONArray(json)
            (0 until array.length()).map { array.getInt(it) }
        } catch (e: Exception) {
            listOf(60, 140)
        }
    }
    
    private fun parseJsonDoubleArray(json: String?): List<Float> {
        if (json.isNullOrEmpty()) return listOf(0.3f, 0.8f)
        return try {
            val array = JSONArray(json)
            (0 until array.length()).map { array.getDouble(it).toFloat() }
        } catch (e: Exception) {
            listOf(0.3f, 0.8f)
        }
    }
    
    private fun saveUserProfile(userId: String, profile: UserProfile) {
        // Implementación para guardar perfil en base de datos
    }
    
    /**
     * Limpiar recursos
     */
    fun cleanup() {
        recommendationScope.cancel()
        recommendationCache.clear()
    }
}

// Data classes

data class UserProfile(
    val favoriteGenres: MutableList<String> = mutableListOf(),
    val favoriteArtists: MutableList<Long> = mutableListOf(),
    val avgSessionDuration: Double = 0.0,
    val preferredBpmRange: MutableList<Int> = mutableListOf(60, 140),
    val preferredEnergyRange: MutableList<Float> = mutableListOf(0.3f, 0.8f),
    val discoveryTaste: Float = 0.5f
)

data class SongInteraction(
    val songId: Long,
    val title: String,
    val artistId: Long,
    val bpm: Int?,
    val energyLevel: Float?,
    val interactionType: String,
    val timestamp: String
)

data class SongDetails(
    val songId: Long,
    val title: String,
    val artist: String,
    val artistId: Long,
    val bpm: Int?,
    val energyLevel: Float?,
    val popularityScore: Float,
    val album: String,
    val thumbnailUrl: String,
    val youtubeUrl: String
)

enum class RecommendationContext {
    GENERAL, SEARCH, PLAYER, HOME
}
