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
    fun add(a: Int, b: Int): Int // … method body omitted (4 lines)
    
    fun multiply(a: Int, b: Int): Int {
        val result = a * b
    fun multiply(a: Int, b: Int): Int // … method body omitted (3 lines)
    
    fun getHistory(): List<String> {
        return history.toList()
    }
    
    private fun validateInput(value: Int): Boolean {
        if (!value.toString().matches(Regex("^-?\\d+$"))) {
    private fun validateInput(value: Int): Boolean // … method body omitted (9 lines)
}

fun processUserData(users: List<User>): Pair<List<User>, List<User>> {
    val valid = mutableListOf<User>()
    val invalid = mutableListOf<User>()
    
fun processUserData(users: List<User>): Pair<List<User>, List<User>> // … function body omitted (10 lines)

// Lambda functions for testing different function types
val simpleArrow = { "simple" }

val complexArrow: (List<String>) -> String = { data ->
    val processed = data
        .filter { it.isNotEmpty() }
    // … lambda_body omitted (4 lines)
}

suspend fun asyncFunction(url: String): String {
    return try {
        val response = fetchData(url)
        
suspend fun asyncFunction(url: String): String // … function body omitted (10 lines)

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
fun <T> processArray(items: List<T>, processor: (T) -> T): List<T> // … function body omitted (10 lines)

// Extension function
fun String.toTitleCase(): String {
    return split(" ")
        .joinToString(" ") { word ->
fun String.toTitleCase(): String // … function body omitted (4 lines)

// Default export function
fun main() {
    val calc = Calculator("test")
    println(calc.add(2, 3))
fun main() // … function body omitted (10 lines)

// Stub for example
data class Response(val isSuccessful: Boolean, val statusCode: Int, val body: String)
suspend fun fetchData(url: String): Response = Response(true, 200, "data")
