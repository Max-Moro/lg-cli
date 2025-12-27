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

// … 17 imports omitted (21 lines)

// Long import lists (candidates for summarization)
import io.ktor.server.application.Application
import io.ktor.server.application.call
import io.ktor.server.application.install
import io.ktor.server.response.respond
import io.ktor.server.response.respondText
import io.ktor.server.routing.Route
import io.ktor.server.routing.get
import io.ktor.server.routing.post
import io.ktor.server.routing.put
import io.ktor.server.routing.delete
import io.ktor.server.routing.routing
import io.ktor.http.HttpStatusCode
import io.ktor.http.Headers
import io.ktor.http.ContentType
import io.ktor.http.Parameters

import org.koin.core.component.KoinComponent
import org.koin.core.component.inject
import org.koin.core.context.startKoin
import org.koin.core.context.stopKoin
import org.koin.core.module.Module
import org.koin.core.module.dsl.singleOf
import org.koin.core.module.dsl.factoryOf
import org.koin.core.qualifier.named
import org.koin.dsl.module
import org.koin.dsl.bind
import org.koin.dsl.binds

import javax.validation.constraints.NotNull
import javax.validation.constraints.NotEmpty
import javax.validation.constraints.NotBlank
import javax.validation.constraints.Email
import javax.validation.constraints.Size
import javax.validation.constraints.Min
import javax.validation.constraints.Max
import javax.validation.constraints.Pattern
import javax.validation.constraints.Positive
import javax.validation.constraints.PositiveOrZero
import javax.validation.constraints.Negative
import javax.validation.constraints.NegativeOrZero
import javax.validation.Valid

// … 23 imports omitted (24 lines)

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
