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
by the literal optimizer when budgets are small. It repeats a message…""" // literal string (−4 tokens)

val BIG_OBJECT = mapOf(
    "users" to (1..50).map { i ->
        // … lambda body omitted (5 lines)},
    // … (1 more, −52 tokens)
)

class PublicService {
    // … property omitted

    /**
     * Public API: gets a user by ID.
     */
    fun getUser(id: Long): User? {
        return cache[id.toString()]
    }

    // … comment omitted
    // … method omitted (7 lines)

    /** Long method body to allow function body stripping. */
    fun process(list: List<User>): ApiResponse<List<User>> {
        // … method body omitted (12 lines)
    }
}

// … class omitted (4 lines)

fun publicFunction(name: String): String {
    // … function body omitted (2 lines)
}

// … function omitted (4 lines)

fun main() {
    // … function body omitted (2 lines)
}

// … comment omitted
data class User(val id: Long, val name: String, val email: String)
data class ApiResponse<T>(val success: Boolean, val data: T)
fun toTitle(text: String): String = text.replaceFirstChar { it.uppercase() }
