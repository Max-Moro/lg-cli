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
    
    fun add(a: Int, b: Int): Int // … method body omitted (6 lines)
    
    fun multiply(a: Int, b: Int): Int // … method body omitted (5 lines)
    
    fun getHistory(): List<String> // … method body omitted (3 lines)
    
    private fun validateInput(value: Int): Boolean // … method body omitted (11 lines)
}

fun processUserData(users: List<User>): Pair<List<User>, List<User>> // … function body omitted (14 lines)

// Lambda functions for testing different function types
val simpleArrow = { "simple" }

val complexArrow: (List<String>) -> String = { data ->
    // … lambda_body omitted (6 lines)
}

suspend fun asyncFunction(url: String): String // … function body omitted (14 lines)

// Function with multiple overloads
fun overloadedFunction(value: String): String // … function body omitted (3 lines)

fun overloadedFunction(value: Int): Int // … function body omitted (3 lines)

// Generic function
fun <T> processArray(items: List<T>, processor: (T) -> T): List<T> // … function body omitted (14 lines)

// Extension function
fun String.toTitleCase(): String // … function body omitted (7 lines)

// Default export function
fun main() // … function body omitted (13 lines)

// Stub for example
data class Response(val isSuccessful: Boolean, val statusCode: Int, val body: String)
suspend fun fetchData(url: String): Response = Response(true, 200, "data")
