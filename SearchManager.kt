package com.musicplayer.search

import android.content.Context
import android.database.Cursor
import android.database.sqlite.SQLiteDatabase
import kotlinx.coroutines.*
import org.json.JSONArray
import org.json.JSONObject
import java.util.*
import kotlin.math.abs
import kotlin.math.max
import kotlin.math.min

/**
 * Motor de Búsqueda Avanzado para Reproductor de Música
 * Implementa Query Expansion, Fuzzy Search y Content-Based Filtering
 */
class SearchManager private constructor(private val context: Context) {
    
    private val database: SQLiteDatabase by lazy { MusicDatabase.getInstance(context) }
    private val searchScope = CoroutineScope(Dispatchers.IO + SupervisorJob())
    private val cache = LRUCache<String, List<SearchResult>>(100)
    
    data class SearchResult(
        val songId: Long,
        val title: String,
        val artist: String,
        val album: String,
        val thumbnailUrl: String,
        val youtubeUrl: String,
        val relevanceScore: Float,
        val matchType: MatchType,
        val artistId: Long,
        val popularityScore: Float
    )
    
    enum class MatchType {
        EXACT, FUZZY, RELATED_ARTIST, SAME_ALBUM, TRENDING
    }
    
    companion object {
        @Volatile
        private var INSTANCE: SearchManager? = null
        
        fun getInstance(context: Context): SearchManager {
            return INSTANCE ?: synchronized(this) {
                INSTANCE ?: SearchManager(context.applicationContext).also { INSTANCE = it }
            }
        }
    }
    
    /**
     * Búsqueda principal con Query Expansion y Fuzzy Search
     */
    suspend fun searchSongs(
        query: String,
        limit: Int = 20,
        userId: String? = null
    ): List<SearchResult> = withContext(Dispatchers.IO) {
        val cacheKey = "${query}_${limit}_${userId}"
        
        // Verificar caché
        cache.get(cacheKey)?.let { return@withContext it }
        
        val results = mutableListOf<SearchResult>()
        
        // 1. Query Expansion
        val expandedQueries = expandQuery(query)
        val normalizedQuery = normalizeString(query)
        
        // 2. Búsqueda exacta (máxima prioridad)
        val exactMatches = searchExactMatches(expandedQueries, limit)
        results.addAll(exactMatches)
        
        // 3. Búsqueda fuzzy
        if (results.size < limit) {
            val fuzzyMatches = searchFuzzyMatches(normalizedQuery, limit - results.size)
            results.addAll(fuzzyMatches)
        }
        
        // 4. Expansión por artista
        if (results.size < limit) {
            val artistMatches = searchArtistRelated(results, limit - results.size)
            results.addAll(artistMatches)
        }
        
        // 5. Personalización basada en historial
        userId?.let {
            personalizeResults(it, results)
        }
        
        // 6. Ordenar por relevancia y limitar
        val sortedResults = results
            .sortedByDescending { it.relevanceScore }
            .take(limit)
        
        // Guardar en caché
        cache.put(cacheKey, sortedResults)
        
        sortedResults
    }
    
    /**
     * Expansión de consulta con términos relacionados
     */
    private fun expandQuery(query: String): List<String> {
        val expansions = mutableSetOf<String>()
        val words = query.split("\\s+".toRegex())
        
        // Agregar consulta original
        expansions.add(query)
        
        // Agregar palabras individuales
        words.filter { it.length > 2 }.forEach { expansions.add(it) }
        
        // Agregar variaciones comunes
        val variations = mapOf(
            "rock" to listOf("rock en español", "rock latino", "alternativo"),
            "pop" to listOf("pop latino", "indie pop", "synth pop"),
            "trap" to listOf("trap latino", "trap malandro", "drill"),
            "reggaeton" to listOf("reggaetón", "latin trap", "perreo"),
            "salsa" to listOf("salsa cubana", "salsa colombiana", "timba"),
            "bachata" to listOf("bachata moderna", "bachata urbana"),
            "cumbia" to listOf("cumbia peruana", "cumbia colombiana", "cumbia villera")
        )
        
        words.forEach { word ->
            val wordLower = word.lowercase(Locale.getDefault())
            variations[wordLower]?.forEach { variation ->
                expansions.add(variation)
            }
        }
        
        return expansions.toList()
    }
    
    /**
     * Normalizar texto para búsqueda fuzzy
     */
    private fun normalizeString(text: String): String {
        return text.lowercase(Locale.getDefault())
            .replace("[^\\w\\s]".toRegex(), "")
            .replace("\\s+".toRegex(), " ")
            .trim()
    }
    
    /**
     * Calcular distancia de Levenshtein
     */
    private fun levenshteinDistance(s1: String, s2: String): Int {
        if (s1.length < s2.length) {
            return levenshteinDistance(s2, s1)
        }
        
        if (s2.isEmpty()) {
            return s1.length
        }
        
        var previousRow = IntRange(0, s2.length).toList()
        
        s1.forEachIndexed { i, c1 ->
            val currentRow = mutableListOf(i + 1)
            
            s2.forEachIndexed { j, c2 ->
                val insertions = previousRow[j + 1] + 1
                val deletions = currentRow[j] + 1
                val substitutions = previousRow[j] + if (c1 != c2) 1 else 0
                currentRow.add(minOf(insertions, deletions, substitutions))
            }
            
            previousRow = currentRow
        }
        
        return previousRow.last()
    }
    
    /**
     * Calcular score de similitud (0-1)
     */
    private fun similarityScore(s1: String, s2: String): Float {
        if (s1.isEmpty() || s2.isEmpty()) {
            return 0f
        }
        
        // Similitud de Levenshtein
        val levDistance = levenshteinDistance(s1.lowercase(), s2.lowercase())
        val maxLength = max(s1.length, s2.length)
        val levSimilarity = if (maxLength > 0) {
            1f - (levDistance.toFloat() / maxLength)
        } else {
            0f
        }
        
        // Similitud de secuencia
        val seqSimilarity = calculateSequenceSimilarity(s1, s2)
        
        // Combinación ponderada
        return levSimilarity * 0.6f + seqSimilarity * 0.4f
    }
    
    /**
     * Calcular similitud de secuencia
     */
    private fun calculateSequenceSimilarity(s1: String, s2: String): Float {
        val s1Lower = s1.lowercase()
        val s2Lower = s2.lowercase()
        
        var matches = 0
        val minLength = min(s1Lower.length, s2Lower.length)
        
        for (i in 0 until minLength) {
            if (s1Lower[i] == s2Lower[i]) {
                matches++
            }
        }
        
        return matches.toFloat() / max(s1Lower.length, s2Lower.length)
    }
    
    /**
     * Búsqueda de coincidencias exactas
     */
    private suspend fun searchExactMatches(queries: List<String], limit: Int): List<SearchResult> = withContext(Dispatchers.IO) {
        val results = mutableListOf<SearchResult>()
        
        queries.take(3).forEach { query ->
            val cursor = database.rawQuery(
                """
                SELECT s.*, a.name as artist_name, al.title as album_title
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                LEFT JOIN albums al ON s.album_id = al.album_id
                WHERE s.title LIKE ? OR a.name LIKE ?
                ORDER BY s.popularity_score DESC
                LIMIT ?
                """.trimIndent(),
                arrayOf("%$query%", "%$query%", limit.toString())
            )
            
            cursor.use { c ->
                while (c.moveToNext()) {
                    val result = cursorToSearchResult(c, MatchType.EXACT) { q, title, artist ->
                        calculateRelevanceScore(q, title, artist, MatchType.EXACT)
                    }
                    results.add(result)
                }
            }
        }
        
        results
    }
    
    /**
     * Búsqueda fuzzy
     */
    private suspend fun searchFuzzyMatches(normalizedQuery: String, limit: Int): List<SearchResult> = withContext(Dispatchers.IO) {
        val results = mutableListOf<SearchResult>()
        
        // Obtener candidatos (limitar para rendimiento)
        val cursor = database.rawQuery(
            """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            ORDER BY s.popularity_score DESC
            LIMIT 100
            """.trimIndent(),
            null
        )
        
        cursor.use { c ->
            val fuzzyResults = mutableListOf<Pair<Float, Cursor>>()
            
            while (c.moveToNext()) {
                val title = c.getString(c.getColumnIndexOrThrow("title"))
                val artist = c.getString(c.getColumnIndexOrThrow("artist_name"))
                
                val titleSimilarity = similarityScore(normalizedQuery, normalizeString(title))
                val artistSimilarity = similarityScore(normalizedQuery, normalizeString(artist))
                
                val bestSimilarity = max(titleSimilarity, artistSimilarity)
                
                if (bestSimilarity > 0.6f) { // Umbral para matching fuzzy
                    val popularity = c.getFloat(c.getColumnIndexOrThrow("popularity_score"))
                    val relevance = bestSimilarity * 0.7f + (popularity / 100f) * 0.3f
                    
                    fuzzyResults.add(Pair(relevance, c))
                }
            }
            
            // Ordenar por relevancia y tomar los mejores
            fuzzyResults.sortByDescending { it.first }
            
            fuzzyResults.take(limit).forEach { (relevance, c) ->
                val result = cursorToSearchResult(c, MatchType.FUZZY) { _, _, _ -> relevance }
                results.add(result)
            }
        }
        
        results
    }
    
    /**
     * Búsqueda de canciones relacionadas por artista
     */
    private suspend fun searchArtistRelated(existingResults: List<SearchResult>, limit: Int): List<SearchResult> = withContext(Dispatchers.IO) {
        val results = mutableListOf<SearchResult>()
        
        // Obtener IDs únicos de artistas de los resultados existentes
        val artistIds = existingResults.take(5).map { it.artistId }.distinct()
        
        artistIds.forEach { artistId ->
            val existingSongIds = existingResults.map { it.songId }.joinToString(",")
            
            val cursor = database.rawQuery(
                """
                SELECT s.*, a.name as artist_name, al.title as album_title
                FROM songs s
                JOIN artists a ON s.artist_id = a.artist_id
                LEFT JOIN albums al ON s.album_id = al.album_id
                WHERE s.artist_id = ? AND s.song_id NOT IN ($existingSongIds)
                ORDER BY s.popularity_score DESC
                LIMIT 3
                """.trimIndent(),
                arrayOf(artistId.toString())
            )
            
            cursor.use { c ->
                while (c.moveToNext()) {
                    val popularity = c.getFloat(c.getColumnIndexOrThrow("popularity_score"))
                    val relevance = 0.6f + (popularity / 100f) * 0.4f
                    
                    val result = cursorToSearchResult(c, MatchType.RELATED_ARTIST) { _, _, _ -> relevance }
                    results.add(result)
                }
            }
        }
        
        results.take(limit)
    }
    
    /**
     * Personalizar resultados basados en el historial del usuario
     */
    private suspend fun personalizeResults(userId: String, results: MutableList<SearchResult>) = withContext(Dispatchers.IO) {
        try {
            // Obtener perfil del usuario
            val profileCursor = database.rawQuery(
                "SELECT * FROM user_profile WHERE user_id = ?",
                arrayOf(userId)
            )
            
            val userProfile = profileCursor.use { c ->
                if (c.moveToFirst()) {
                    mapOf(
                        "favorite_genres" to JSONArray(c.getString(c.getColumnIndexOrThrow("favorite_genres"))),
                        "favorite_artists" to JSONArray(c.getString(c.getColumnIndexOrThrow("favorite_artists")))
                    )
                } else null
            }
            
            userProfile?.let { profile ->
                val favoriteGenres = mutableListOf<String>()
                val favoriteArtists = mutableListOf<Long>()
                
                // Parsear géneros favoritos
                val genresArray = profile["favorite_genres"] as JSONArray
                for (i in 0 until genresArray.length()) {
                    favoriteGenres.add(genresArray.getString(i))
                }
                
                // Parsear artistas favoritos
                val artistsArray = profile["favorite_artists"] as JSONArray
                for (i in 0 until artistsArray.length()) {
                    favoriteArtists.add(artistsArray.getLong(i))
                }
                
                // Boost de scores basado en preferencias
                results.forEach { result ->
                    // Obtener géneros de la canción
                    val genreCursor = database.rawQuery(
                        """
                        SELECT g.name FROM genres g
                        JOIN artist_genres ag ON g.genre_id = ag.genre_id
                        WHERE ag.artist_id = ?
                        """.trimIndent(),
                        arrayOf(result.artistId.toString())
                    )
                    
                    val songGenres = mutableListOf<String>()
                    genreCursor.use { c ->
                        while (c.moveToNext()) {
                            songGenres.add(c.getString(0))
                        }
                    }
                    
                    // Boost para géneros favoritos
                    val genreBoost = if (songGenres.any { it in favoriteGenres }) 0.1f else 0f
                    
                    // Boost para artistas favoritos
                    val artistBoost = if (result.artistId in favoriteArtists) 0.15f else 0f
                    
                    // Aplicar boosts
                    result.relevanceScore += genreBoost + artistBoost
                }
            }
        } catch (e: Exception) {
            // Log error but don't fail the search
            e.printStackTrace()
        }
    }
    
    /**
     * Convert cursor to SearchResult
     */
    private fun cursorToSearchResult(
        cursor: Cursor,
        matchType: MatchType,
        relevanceCalculator: (String, String, String) -> Float
    ): SearchResult {
        val songId = cursor.getLong(cursor.getColumnIndexOrThrow("song_id"))
        val title = cursor.getString(cursor.getColumnIndexOrThrow("title"))
        val artist = cursor.getString(cursor.getColumnIndexOrThrow("artist_name"))
        val album = cursor.getString(cursor.getColumnIndexOrThrow("album_title")) ?: "Unknown Album"
        val thumbnailUrl = cursor.getString(cursor.getColumnIndexOrThrow("thumbnail_url")) ?: ""
        val youtubeUrl = cursor.getString(cursor.getColumnIndexOrThrow("youtube_url")) ?: ""
        val popularityScore = cursor.getFloat(cursor.getColumnIndexOrThrow("popularity_score"))
        val artistId = cursor.getLong(cursor.getColumnIndexOrThrow("artist_id"))
        
        val relevanceScore = relevanceCalculator("", title, artist)
        
        return SearchResult(
            songId = songId,
            title = title,
            artist = artist,
            album = album,
            thumbnailUrl = thumbnailUrl,
            youtubeUrl = youtubeUrl,
            relevanceScore = relevanceScore,
            matchType = matchType,
            artistId = artistId,
            popularityScore = popularityScore
        )
    }
    
    /**
     * Calcular score de relevancia
     */
    private fun calculateRelevanceScore(
        query: String,
        title: String,
        artist: String,
        matchType: MatchType
    ): Float {
        val baseScore = when (matchType) {
            MatchType.EXACT -> 1.0f
            MatchType.FUZZY -> 0.7f
            MatchType.RELATED_ARTIST -> 0.6f
            MatchType.SAME_ALBUM -> 0.5f
            MatchType.TRENDING -> 0.4f
        }
        
        var score = baseScore
        
        // Boost para coincidencias exactas en título
        if (query.lowercase() in title.lowercase()) {
            score += 0.2f
        }
        
        // Boost para coincidencias exactas en artista
        if (query.lowercase() in artist.lowercase()) {
            score += 0.15f
        }
        
        return min(score, 1.0f)
    }
    
    /**
     * Obtener canciones populares de un artista
     */
    suspend fun getArtistSongs(artistId: Long, limit: Int = 20): List<SearchResult> = withContext(Dispatchers.IO) {
        val cursor = database.rawQuery(
            """
            SELECT s.*, a.name as artist_name, al.title as album_title
            FROM songs s
            JOIN artists a ON s.artist_id = a.artist_id
            LEFT JOIN albums al ON s.album_id = al.album_id
            WHERE s.artist_id = ?
            ORDER BY s.popularity_score DESC, s.play_count DESC
            LIMIT ?
            """.trimIndent(),
            arrayOf(artistId.toString(), limit.toString())
        )
        
        val results = mutableListOf<SearchResult>()
        
        cursor.use { c ->
            while (c.moveToNext()) {
                val result = cursorToSearchResult(c, MatchType.RELATED_ARTIST) { _, _, _ ->
                    c.getFloat(c.getColumnIndexOrThrow("popularity_score")) / 100f
                }
                results.add(result)
            }
        }
        
        results
    }
    
    /**
     * Actualizar interacción del usuario
     */
    suspend fun updateUserInteraction(userId: String, songId: Long, interactionType: String) = withContext(Dispatchers.IO) {
        // Registrar interacción
        database.execSQL(
            "INSERT INTO user_interactions (user_id, song_id, interaction_type, timestamp) VALUES (?, ?, ?, datetime('now'))",
            arrayOf(userId, songId.toString(), interactionType)
        )
        
        // Actualizar contador de reproducciones
        if (interactionType == "play") {
            database.execSQL(
                "UPDATE songs SET play_count = play_count + 1, last_played = datetime('now') WHERE song_id = ?",
                arrayOf(songId.toString())
            )
        }
    }
    
    /**
     * Limpiar recursos
     */
    fun cleanup() {
        searchScope.cancel()
        cache.clear()
    }
}

/**
 * Cache LRU simple para resultados de búsqueda
 */
class LRUCache<K, V>(private val capacity: Int) {
    private val cache = LinkedHashMap<K, V>(capacity, 0.75f, true)
    
    fun get(key: K): V? {
        return cache[key]
    }
    
    fun put(key: K, value: V) {
        if (cache.size >= capacity) {
            cache.remove(cache.keys.first())
        }
        cache[key] = value
    }
    
    fun clear() {
        cache.clear()
    }
}
