/** … docstring omitted */

package com.example.comments

// … comment omitted
object Constants {
  val MODULE_VERSION = "1.0.0" // … comment omitted
}

/** … docstring omitted */
case class User(
  id: Long,        // … comment omitted
  name: String,    // … comment omitted
  email: String,   // … comment omitted
  // … comment omitted
  profile: Option[Profile] = None
)

case class Profile(
  bio: String,
  avatar: Option[String] = None
)

class CommentedService(
  private val config: ServiceConfig,  // … comment omitted
  private val logger: Option[Logger] = None  // … comment omitted
) {
  /** … docstring omitted */
  initialize()

  // … comment omitted

  /** … docstring omitted */
  def processUser(userData: Map[String, Any]): User = {
    // … comment omitted
    if (userData.isEmpty) {
      throw new IllegalArgumentException("User data is required")
    }

    // … comment omitted
    val validationResult = validateUser(userData)
    if (!validationResult.isValid) {
      // … comment omitted
      logger.foreach(_.error(s"Validation failed: ${validationResult.errors}"))
      throw new ValidationException(validationResult.errors)
    }

    // … comment omitted
    val transformedData = transformUserData(userData)

    // … comment omitted
    val savedUser = saveUser(transformedData)

    savedUser  // … comment omitted
  }

  private def validateUser(userData: Map[String, Any]): ValidationResult = {
    // … comment omitted
    val errors = scala.collection.mutable.ListBuffer[String]()

    // … comment omitted
    if (!userData.contains("name")) {
      errors += "Name is required"  // … comment omitted
    }

    if (!userData.contains("email")) {
      errors += "Email is required"
    }

    // … comment omitted
    val emailRegex = "^[^\\s@]+@[^\\s@]+\\.[^\\s@]+$".r
    userData.get("email").foreach { email =>
      if (!emailRegex.matches(email.toString)) {
        errors += "Invalid email format"
      }
    }

    ValidationResult(
      isValid = errors.isEmpty,
      errors = errors.toList
    )
  }

  // … comment omitted
  private def transformUserData(userData: Map[String, Any]): User = {
    // … comment omitted
    User(
      id = generateUserId(),    // … comment omitted
      name = userData("name").toString.trim,  // … comment omitted
      email = userData("email").toString.toLowerCase,  // … comment omitted
      profile = userData.get("profile").map(_.asInstanceOf[Profile])
        .orElse(Some(Profile("")))  // … comment omitted
    )
  }

  /** … docstring omitted */
  private def generateUserId(): Long = {
    // … comment omitted
    (Math.random() * 1000000).toLong
  }

  // … comment omitted
  private def saveUser(user: User): User = {
    // … comment omitted
    logger.foreach(_.info(s"Saving user: ${user.id}"))

    // … comment omitted
    Thread.sleep(100)

    user  // … comment omitted
  }

  private def initialize(): Unit = {
    // … comment omitted
  }
}

/** … docstring omitted */
def processString(input: String): String = {
  // … comment omitted
  if (input.isEmpty) {
    return ""  // … comment omitted
  }

  // … comment omitted
  val trimmed = input.trim
  val lowercase = trimmed.toLowerCase
  val cleaned = lowercase.replaceAll("[^a-z0-9\\s]", "")

  cleaned  // … comment omitted
}

// … comment omitted
def undocumentedHelper(): Unit = {
  // … comment omitted
  val data = "helper data"

  // … comment omitted
  println(data)  // … comment omitted
}

// … comment omitted
case class ValidationResult(
  isValid: Boolean,     // … comment omitted
  errors: List[String]  // … comment omitted
)

case class ServiceConfig(
  // … comment omitted
  timeout: Long,      // … comment omitted
  retries: Int,       // … comment omitted
  baseUrl: String     // … comment omitted
)

// … comment omitted
trait Logger {
  def info(message: String, data: Any = null): Unit    // … comment omitted
  def error(message: String, data: Any = null): Unit   // … comment omitted
  def warn(message: String, data: Any = null): Unit    // … comment omitted
}

// … comment omitted
class ValidationException(val errors: List[String]) extends Exception {
  override def getMessage: String = s"Validation failed: ${errors.mkString(", ")}"
}

// … comment omitted
object DefaultConfig {
  val DEFAULT_CONFIG = ServiceConfig(
    timeout = 5000,    // … comment omitted
    retries = 3,       // … comment omitted
    baseUrl = "http://localhost:3000"  // … comment omitted
  )
}
