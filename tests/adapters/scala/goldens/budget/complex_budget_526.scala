/**
 * Comprehensive Scala sample for Budget System tests.
 * Contains:
 * - External imports
 * - Local imports
 * - Long comments and Scaladoc
 * - Big literals (lists/maps/multiline strings)
 * - Public vs private API elements
 */

package com.example.budget

// … 8 imports omitted (6 lines)

// … comment omitted
import com.example.budget.types.{User, ApiResponse}
import com.example.budget.utils.strings.toTitle

/**
 * Module level long documentation that might be truncated under tight budgets.
 * The text includes several sentences to ensure the comment optimizer has
 * something to work with when switching to keep_first_sentence mode.
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
  private val cache = mutable.Map.empty[String, User]

  /**
   * Public API: gets a user by ID.
   * This doc has multiple sentences to allow truncation under budget.
   */
  def getUser(id: Long): Option[User] = {
    cache.get(id.toString)
  }

  // … comment omitted
  private def normalize(u: Map[String, Any]): User = {
    User(
      id = u("id").asInstanceOf[Long],
      name = u.getOrElse("name", "").toString.trim,
      email = u.getOrElse("email", "").toString
    )
  }

  /** Long method body to allow function body stripping */
  def process(list: List[User]): ApiResponse[List[User]] = {
    val out = mutable.ListBuffer.empty[User]
    for (u <- list) {
      val n = normalize(
        Map(
          "id" -> u.id,
          "name" -> u.name,
          "email" -> u.email
        )
      )
      out += n
    }
    ApiResponse(success = true, data = out.toList)
  }
}

private class InternalOnly {
  // … comment omitted
  def doWork(): Unit = { // … comment omitted }
}

object Functions {
  def publicFunction(name: String): String = {
    // … comment omitted
    toTitle.map(_(name)).getOrElse(name)
  }

  private def privateFunction(data: List[String]): List[String] = {
    // … comment omitted
    data.map(_.trim)
  }
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
