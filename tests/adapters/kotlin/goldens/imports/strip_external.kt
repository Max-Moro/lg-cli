/**
 * Kotlin module for testing import optimization.
 */

package com.example.imports

// … 22 imports omitted (24 lines)

// Local/relative imports (should be considered local)
import com.example.imports.services.UserService
import com.example.imports.database.DatabaseConnection
import com.example.imports.errors.ValidationError
import com.example.imports.errors.NetworkError
import com.example.imports.utils.helpers.formatDate
import com.example.imports.utils.helpers.parseJson
import com.example.imports.types.ApiResponse
import com.example.imports.types.UserModel
import com.example.imports.types.PostModel

// Relative imports with different depth levels
import com.example.shared.SharedUtility
import com.example.core.CoreModule
import com.example.config.AppConfig

// Import with aliasing
import com.example.imports.utils.logger.Logger as AppLogger
import com.example.imports.config.Config as AppConfig2
import com.example.imports.http.HttpClient as CustomHttpClient

// Star imports
import com.example.imports.extensions.*
import com.example.imports.constants.*

// … 39 imports omitted (40 lines)

// Local imports with long lists
import com.example.imports.services.createUser
import com.example.imports.services.updateUser
import com.example.imports.services.deleteUser
import com.example.imports.services.getUserById
import com.example.imports.services.getUserByEmail
import com.example.imports.services.getUsersByRole
import com.example.imports.services.getUsersWithPagination
import com.example.imports.services.activateUser
import com.example.imports.services.deactivateUser
import com.example.imports.services.resetUserPassword
import com.example.imports.services.changeUserRole
import com.example.imports.services.validateUserPermissions

import com.example.utils.validation.validateEmail
import com.example.utils.validation.validatePassword
import com.example.utils.validation.validatePhoneNumber
import com.example.utils.validation.validatePostalCode
import com.example.utils.validation.validateCreditCard
import com.example.utils.validation.sanitizeInput
import com.example.utils.validation.formatCurrency
import com.example.utils.validation.formatPhoneNumber
import com.example.utils.validation.generateSlug
import com.example.utils.validation.createHash
import com.example.utils.validation.verifyHash

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
