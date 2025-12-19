/**
 * Comprehensive Scala sample for Budget System tests.
 */

package com.example.budget

// … comment omitted
// … 8 imports omitted

// … comment omitted
// … 3 imports omitted

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
object ModuleConstants {
  val MODULE_TITLE = "Budget System Complex Sample"

  val LONG_TEXT = """This is an extremely long raw string that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message to…""" // literal string (−5 tokens)

  val BIG_OBJECT = Map(
    "users" -> (1 to 50).map { i =>
      Map(
        "id" -> i,
        "name" -> s"User $i",
        // … (1 more, −13 tokens)
      )
    }.toList,
    // … (1 more, −55 tokens)
  )
}

class PublicService {
  // … val omitted

  /**
   * Public API: gets a user by ID.
   */
  def getUser(id: Long): Option[User] = // … method body omitted (3 lines)

  // … comment omitted
  // … method omitted

  /** Long method body to allow function body stripping. */
  def process(list: List[User]): ApiResponse[List[User]] = // … method body omitted (14 lines)
}

// … class omitted

object Functions {
  def publicFunction(name: String): String = // … method body omitted (4 lines)

  // … method omitted
}

object Main extends App {
  val svc = new PublicService()
  println(svc.getUser(1))
}

// … comment omitted
case class User(id: Long, name: String, email: String)
case class ApiResponse[T](success: Boolean, data: T)

object StringUtils {
  def toTitle(text: String): String = // … method body omitted (3 lines)
}
