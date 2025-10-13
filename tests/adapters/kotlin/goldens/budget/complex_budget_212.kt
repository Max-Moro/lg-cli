
/**
 * Comprehensive Kotlin sample for Budget System tests.
 */

package com.example.budget







/**
 * Module level long documentation that might be truncated under tight budgets.
 */
const val MODULE_TITLE = "Budget System Complex Sample"

val LONG_TEXT = """This is an extremely long raw string that is designed to be trimmed 
by the literal optimizer when budgets are small. It repeats a message…"""

val BIG_OBJECT = mapOf(
    "…" to "…"
) // literal object (−99 tokens)

class PublicService {
    

    /**
     * Public API: gets a user by ID.
     */
    fun getUser(id: Long): User? 

    
    

    /**
     * Long method body to allow function body stripping.
     */
    fun process(list: List<User>): ApiResponse<List<User>> 
}



fun publicFunction(name: String): String 



fun main() 


data class User(val id: Long, val name: String, val email: String)
data class ApiResponse<T>(val success: Boolean, val data: T)
fun toTitle(text: String): String
