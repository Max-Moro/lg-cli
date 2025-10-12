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
        history.add("add($a, $b) = $result")
        println("Addition result: $result")
        return result
    }
    
    fun multiply(a: Int, b: Int): Int {
        val result = a * b
        history.add("multiply($a, $b) = $result")
        return result
    }
    
    fun getHistory(): List<String> {
        return history.toList()
    }
    
    private fun validateInput(value: Int): Boolean {
        if (!value.toString().matches(Regex("^-?\\d+$"))) {
            throw IllegalArgumentException("Input must be a number")
        }
        
        if (abs(value) == Int.MAX_VALUE) {
            throw IllegalArgumentException("Input must be finite")
        }
        
        return true
    }
}

fun processUserData(users: List<User>): Pair<List<User>, List<User>> {
    val valid = mutableListOf<User>()
    val invalid = mutableListOf<User>()
    
    for (user in users) {
        if (user.id > 0 && user.name.isNotEmpty() && user.email.contains('@')) {
            valid.add(user)
        } else {
            invalid.add(user)
        }
    }
    
    return Pair(valid, invalid)
}

// Lambda functions for testing different function types
val simpleArrow = { "simple" }

val complexArrow: (List<String>) -> String = { data ->
    val processed = data
        .filter { it.isNotEmpty() }
        .map { it.trim() }
        .sorted()
    
    processed.joinToString(", ")
}

suspend fun asyncFunction(url: String): String {
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
    
    for (item in items) {
        try {
            val processed = processor(item)
            result.add(processed)
        } catch (e: Exception) {
            println("Processing failed for item: $item")
        }
    }
    
    return result
}

// Extension function
fun String.toTitleCase(): String {
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
    println(calc.multiply(4, 5))
    
    val users = listOf(
        User(1, "Alice", "alice@example.com"),
        User(2, "Bob", "bob@example.com")
    )
    
    val (valid, invalid) = processUserData(users)
    println("Valid: $valid")
}

// Stub for example
data class Response(val isSuccessful: Boolean, val statusCode: Int, val body: String)
suspend fun fetchData(url: String): Response = Response(true, 200, "data")

