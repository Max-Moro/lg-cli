// … comment omitted
/**
 * Comprehensive Kotlin sample for Budget System tests.
 */

package com.example.budget

// … comment omitted
// … 5 imports omitted

// … comment omitted
// … 3 imports omitted

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
const val MODULE_TITLE = "Budget System Complex Sample"

val LONG_TEXT = """This is an extremely long raw string that is designed to be trimmed 
by the literal optimizer when budgets are small. It repeats a message…""" // literal string (−7 tokens)

val BIG_OBJECT = mapOf(
    "users" to (1..50).map { i ->
        mapOf(
            "id" to i,
            "name" to "User $i",
            // … (1 more, −13 tokens)
        )
    },
    // … (1 more, −52 tokens)
)

class PublicService {
    // … property omitted

    /**
     * Public API: gets a user by ID.
     */
    fun getUser(id: Long): User? // … method body omitted (3 lines)

    // … comment omitted
    // … method omitted

    /** Long method body to allow function body stripping. */
    fun process(list: List<User>): ApiResponse<List<User>> // … method body omitted (14 lines)
}

// … class omitted

fun publicFunction(name: String): String // … function body omitted (4 lines)

// … function omitted

fun main() // … function body omitted (4 lines)

// … comment omitted
data class User(val id: Long, val name: String, val email: String)
data class ApiResponse<T>(val success: Boolean, val data: T)
fun toTitle(text: String): String // … function body omitted
