/**
 * Comprehensive Scala sample for Budget System tests.
 */

package com.example.budget

// … comment omitted
// … 8 imports omitted (5 lines)

// … comment omitted
// … 3 imports omitted (2 lines)

/**
 * Module level long documentation that might be truncated under tight budgets.
 */
object ModuleConstants {
  val MODULE_TITLE = "Budget System Complex Sample"

  val LONG_TEXT = """This is an extremely long raw string that is designed to be trimmed
by the literal optimizer when budgets are small. It repeats a message to…""" // literal string (−2 tokens)

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
  // … field omitted

  /**
   * Public API: gets a user by ID.
   */
  def getUser(id: Long): Option[User] = {
    cache.get(id.toString)
  }

  // … comment omitted
  // … method omitted (7 lines)

  /** Long method body to allow function body stripping. */
  def process(list: List[User]): ApiResponse[List[User]] = {
    // … method body omitted (12 lines)
  }
}

// … class omitted (4 lines)

object Functions {
  def publicFunction(name: String): String = {
    // … method body omitted (2 lines)
  }

  // … method omitted (4 lines)
}

object Main extends App {
  val svc = new PublicService()
  println(svc.getUser(1))
}

// … comment omitted
case class User(id: Long, name: String, email: String)
case class ApiResponse[T](success: Boolean, data: T)

object StringUtils {
  def toTitle(text: String): String = {
    text.split(" ").map(_.capitalize).mkString(" ")
  }
}
