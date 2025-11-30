/**
 * Scala module for testing function body optimization.
 */

package com.example.test

trait UserRepository {
  def findById(id: Long): Option[User]
  def save(user: User): User
}

case class User(
  id: Long,
  name: String,
  email: String
)

class Calculator(val name: String = "default") {
  private val history: scala.collection.mutable.ListBuffer[String] =
    scala.collection.mutable.ListBuffer.empty

  def add(a: Int, b: Int): Int = // … method body omitted (6 lines)

  def multiply(a: Int, b: Int): Int = // … method body omitted (5 lines)

  def getHistory: List[String] = history.toList

  private def validateInput(value: Int): Boolean = // … method body omitted (11 lines)
}

case class ProcessingResult(
  valid: List[User],
  invalid: List[User]
)

object UserProcessor {
  def processUserData(users: List[User]): ProcessingResult = // … method body omitted (9 lines)
}

// Function with pattern matching
def processValue(value: Any): String = // … function body omitted (6 lines)

// Higher-order function
def processArray[T](items: List[T])(processor: T => T): List[T] = {
  items.map { item =>
    try {
      processor(item)
    } catch {
      case e: Exception =>
        println(s"Processing failed for item: $item")
        item
    }
  }
}

// Implicit class (extension method)
implicit class StringOps(val s: String) extends AnyVal {
  def toTitleCase: String = {
    s.split(" ")
      .map(_.toLowerCase.capitalize)
      .mkString(" ")
  }
}

// Object with apply method
object Main extends App {
  val calc = new Calculator("test")
  println(calc.add(2, 3))
  println(calc.multiply(4, 5))

  val users = List(
    User(1, "Alice", "alice@example.com"),
    User(2, "Bob", "bob@example.com")
  )

  val result = UserProcessor.processUserData(users)
  println(s"Valid: ${result.valid}")
}

// Companion object
class Service private(val config: String) {
  def process(): Unit = // … method body omitted (3 lines)
}

object Service {
  def apply(config: String): Service = new Service(config)

  def default(): Service = new Service("default-config")
}
