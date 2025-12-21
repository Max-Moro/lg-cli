/**
 * Kotlin module for testing function body optimization.
 */

package com.example.test

import kotlin.math.abs

interface UserRepository {
    fun findById(id: Long): User?
    fun save(user: User): User
}

data class User(
    val id: Long,
    val name: String,
    val email: String
)

class Calculator(private val name: String = "default") {
    private val history: MutableList<String> = mutableListOf()
    
    fun add(a: Int, b: Int): Int {
        val result = a + b
        // … method body truncated (2 lines)
        return result
    }
    
    fun multiply(a: Int, b: Int): Int {
        val result = a * b
        // … method body truncated
        return result
    }
    
    fun getHistory(): List<String> {
        return history.toList()
    }
    
    private fun validateInput(value: Int): Boolean {
        if (!value.toString().matches(Regex("^-?\\d+$"))) {
        // … method body truncated (7 lines)
        
        return true
    }
}

fun processUserData(users: List<User>): Pair<List<User>, List<User>> {
    val valid = mutableListOf<User>()
    // … function body truncated (10 lines)
    
    return Pair(valid, invalid)
}

// Lambda functions for testing different function types
val simpleArrow = { "simple" }

val complexArrow: (List<String>) -> String = { data ->
    val processed = data
        .filter { it.isNotEmpty() }
// … lambda_body_truncated omitted (4 lines)
}

suspend fun asyncFunction(url: String): String {    // … function body truncated
    return try {
        val response = fetchData(url)
        
        if (!response.isSuccessful) {
            throw Exception("HTTP ${response.statusCode}")
        }
        
        response.body
    } catch (e: Exception) {
        println("Fetch error: ${e.message}")
        throw e
    }
}

// Function with multiple overloads
fun overloadedFunction(value: String): String {
    return value.uppercase()
}

fun overloadedFunction(value: Int): Int {
    return value * 2
}

// Generic function
fun <T> processArray(items: List<T>, processor: (T) -> T): List<T> {
    val result = mutableListOf<T>()
    
    // … function body truncated (9 lines)
    
    return result
}

// Extension function
fun String.toTitleCase(): String {    // … function body truncated
    return split(" ")
        .joinToString(" ") { word ->
            word.lowercase()
                .replaceFirstChar { it.uppercase() }
        }
}

// Default export function
fun main() {
    val calc = Calculator("test")
    println(calc.add(2, 3))
    // … function body truncated (9 lines)
}

// Stub for example
data class Response(val isSuccessful: Boolean, val statusCode: Int, val body: String)
suspend fun fetchData(url: String): Response = Response(true, 200, "data")
