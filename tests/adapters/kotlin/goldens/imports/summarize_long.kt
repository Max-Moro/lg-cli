/**
 * Kotlin module for testing import optimization.
 */

package com.example.imports

// Standard library imports (external)
import kotlin.math.*
import kotlin.collections.*
import kotlin.text.Regex
import kotlin.io.path.Path
import kotlin.random.Random
import java.time.Instant
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.util.UUID
import java.util.concurrent.ConcurrentHashMap
import java.util.concurrent.atomic.AtomicInteger

// Third-party library imports (external)
import kotlinx.coroutines.*
import kotlinx.coroutines.flow.*
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import io.ktor.client.*
import io.ktor.client.request.*
import io.ktor.client.statement.*
import com.google.gson.Gson
import com.google.gson.GsonBuilder
import org.slf4j.Logger
import org.slf4j.LoggerFactory

// Local/relative imports (should be considered local)
// … 9 imports omitted

// Relative imports with different depth levels
// … 3 imports omitted

// Import with aliasing
// … 3 imports omitted

// Star imports
// … 2 imports omitted

// Long import lists (candidates for summarization)
// … 39 imports omitted

// Local imports with long lists
// … 23 imports omitted

class ImportTestService(
    private val userService: UserService,
    private val dbConnection: DatabaseConnection,
    private val logger: AppLogger
) : KoinComponent {
    
    suspend fun processData(data: List<Any>): ApiResponse<List<Any>> {
        // Using external libraries
        val processed = data.map { item ->
            mapOf(
                "id" to UUID.randomUUID(),
                "timestamp" to Instant.now().toString(),
                "item" to item
            )
        }
        
        // Using local utilities
        val validated = processed.mapNotNull { item ->
            val email = item["email"] as? String
            if (email != null && validateEmail(email)) item else null
        }
        
        // Using Kotlin standard library
        val filePath = Path("/output.json")
        
        return ApiResponse(
            success = true,
            data = validated,
            timestamp = formatDate(LocalDateTime.now())
        )
    }
    
    suspend fun makeHttpRequest(url: String): String? {
        return try {
            // Using Ktor client
            val client = HttpClient()
            val response: HttpResponse = client.get(url) {
                timeout {
                    requestTimeoutMillis = 5000
                }
                headers {
                    append("User-Agent", "ImportTestService/1.0")
                }
            }
            
            response.bodyAsText()
        } catch (e: Exception) {
            logger.error("HTTP request failed", e)
            throw NetworkError("Request failed")
        }
    }
    
    fun serializeData(data: Any): String {
        // Using Gson
        val gson = GsonBuilder()
            .setPrettyPrinting()
            .create()
        
        return gson.toJson(data)
    }
}

// Annotated classes using validation imports
@Serializable
data class ValidatedUser(
    @NotNull
    @NotEmpty
    val id: String,
    
    @NotBlank
    @Size(min = 2, max = 100)
    val name: String,
    
    @Email
    @NotEmpty
    val email: String,
    
    @Positive
    val age: Int?,
    
    @Pattern(regexp = "^\\+?[1-9]\\d{1,14}$")
    val phone: String?
)

// Function using multiple imports
suspend fun processWithCoroutines(items: List<String>): Flow<String> = flow {
    items.forEach { item ->
        delay(100)
        emit(item.uppercase())
    }
}.flowOn(Dispatchers.Default)

// Koin module definition
val appModule = module {
    single { DatabaseConnection(get()) }
    singleOf(::UserService) bind AppLogger::class
    factory { ImportTestService(get(), get(), get()) }
}

// Default export
fun main() {
    startKoin {
        modules(appModule)
    }
    
    val service: ImportTestService by inject()
    println("Service initialized")
}
