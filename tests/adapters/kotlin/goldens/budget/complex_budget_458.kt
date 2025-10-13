
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







/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
 */
const val MODULE_TITLE = "Budget System Complex Sample"

val LONG_TEXT = """This is an extremely long raw string that is designed to be trimmed 
by the literal optimizer when budgets are small. It repeats a message…"""

val BIG_OBJECT = mapOf(
    "…" to "…"
) // literal object (−99 tokens)

class PublicService {
    private val cache = mutableMapOf<String, User>()

    /**
     * Public API: gets a user by ID.
     * This doc has multiple sentences to allow truncation under budget.
     */
    fun getUser(id: Long): User? {
        return cache[id.toString()]
    }

    
    private fun normalize(u: Map<String, Any?>): User 

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

private class InternalOnly {
    
    fun doWork() { /* noop */ }
}

fun publicFunction(name: String): String {
    
    return toTitle?.invoke(name) ?: name
}

private fun privateFunction(data: List<String>): List<String> 

fun main() {
    val svc = PublicService()
    println(svc.getUser(1))
}


data class User(val id: Long, val name: String, val email: String)
data class ApiResponse<T>(val success: Boolean, val data: T)
fun toTitle(text: String): String = text.replaceFirstChar { it.uppercase() }
