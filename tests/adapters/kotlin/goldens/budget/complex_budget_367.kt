// … comment omitted
/**
 * Comprehensive Kotlin sample for Budget System tests.
 * Contains:
 * - External imports
 * - Local imports
 * - Long comments and KDoc
 * - Big literals (lists/maps/raw strings)
 * - Public vs private API elements
 */

package com.example.budget

// … 8 imports omitted (10 lines)

/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
 */
const val MODULE_TITLE = "Budget System Complex Sample"

val LONG_TEXT = """This is an extremely long raw string that is designed to be trimmed 
by the literal optimizer when budgets are small. It repeats a message…""" // literal string (−4 tokens)

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
     * This doc has multiple sentences to allow truncation under budget.
     */
    fun getUser(id: Long): User? {
        return cache[id.toString()]
    }

    // … method omitted (8 lines)

    /** Long method body to allow function body stripping */
    fun process(list: List<User>): ApiResponse<List<User>> {
        val out = mutableListOf<User>()
        for (u in list) {
            val n = normalize(
                mapOf(
                    "id" to u.id,
                    "name" to u.name,
                    "email" to u.email
                )
            )
            out.add(n)
        }
        return ApiResponse(success = true, data = out)
    }
}

// … class omitted (4 lines)

fun publicFunction(name: String): String {
    // … comment omitted
    return toTitle?.invoke(name) ?: name
}

// … function omitted (4 lines)

fun main() {
    val svc = PublicService()
    println(svc.getUser(1))
}

// … comment omitted
data class User(val id: Long, val name: String, val email: String)
data class ApiResponse<T>(val success: Boolean, val data: T)
fun toTitle(text: String): String = text.replaceFirstChar { it.uppercase() }
