/**
 * Scala module for testing public API filtering.
 */

package com.example.publicapi

import java.time.Instant

// Public module-level constants (should be preserved)
object PublicConstants {
  val PUBLIC_VERSION = "1.0.0"
  val API_ENDPOINT = "https://api.example.com"

  // … 2 fields omitted (3 lines)
}

// Public case class (should be preserved)
case class User(
  id: Long,
  name: String,
  email: String,
  createdAt: Instant
)

// … case class omitted (5 lines)

// Public type alias (should be preserved)
type UserRole = String

// Public class with mixed visibility members
class UserManager(private val apiEndpoint: String = PublicConstants.API_ENDPOINT) {
  // Public properties
  val version: String = PublicConstants.PUBLIC_VERSION
  var isInitialized: Boolean = false

  // … 3 fields omitted (7 lines)

  initialize()

  // Public methods (should be preserved)
  def createUser(userData: Map[String, Any]): User = {
    validateUserData(userData)

    val user = User(
      id = generateId(),
      name = userData("name").toString,
      email = userData("email").toString,
      createdAt = Instant.now()
    )

    internalCache(user.email) = user
    user
  }

  def getUserById(id: Long): Option[User] = {
    internalCache.values.find(_.id == id)
      .orElse(fetchUserFromApi(id))
  }

  def getAllUsers: List[User] = {
    internalCache.values.toList
  }

  // … 6 methods omitted (35 lines)

  // Public property with getter
  def userCount: Int = internalCache.size

  // … method omitted (5 lines)
}

// Companion object with mixed visibility
object UserManager {
  // Public static methods (should be preserved)
  def validateUserRole(role: String): Boolean = {
    List("admin", "user", "guest").contains(role)
  }

  def createDefaultUser(): User = {
    User(
      id = 0,
      name = "Default User",
      email = "default@example.com",
      createdAt = Instant.now()
    )
  }

  // … method omitted (4 lines)
}

// … class omitted (12 lines)

// Public abstract class (should be preserved)
abstract class BaseService {
  // … method omitted

  def initialize(): Unit

  def getServiceInfo: Map[String, String] = Map(
    "name" -> serviceName,
    "version" -> PublicConstants.PUBLIC_VERSION
  )

  // … method omitted (2 lines)
}

// Public trait (should be preserved)
trait UserService {
  def findById(id: Long): Option[User]
  def save(user: User): User
}

// … trait omitted (5 lines)

// Public sealed trait with case objects (should be preserved)
sealed trait UserStatus
object UserStatus {
  case object Active extends UserStatus
  case object Inactive extends UserStatus
  case object Pending extends UserStatus
  case object Banned extends UserStatus
}

// … trait omitted (2 lines)
// … object omitted (5 lines)

// Public functions (should be preserved)
def createUserManager(endpoint: Option[String] = None): UserManager = {
  new UserManager(endpoint.getOrElse(PublicConstants.API_ENDPOINT))
}

def isValidUserRole(role: Any): Boolean = {
  UserManager.validateUserRole(role.toString)
}

// … 2 functions omitted (8 lines)

// Public object (should be preserved)
object UserUtils {
  def formatUserName(user: User): String = {
    s"${user.name} (${user.email})"
  }

  def getUserAge(user: User): Long = {
    val now = Instant.now()
    val created = user.createdAt
    (now.toEpochMilli - created.toEpochMilli) / (1000 * 60 * 60 * 24)
  }

  // … method omitted (4 lines)
}

// … object omitted (15 lines)

// ============= Examples with Scala annotations =============

// Simple annotation examples
import scala.annotation.tailrec

class Logged extends scala.annotation.StaticAnnotation
class Validate extends scala.annotation.StaticAnnotation

// … class omitted (11 lines)

@Logged
@Validate
class PublicAnnotatedClass {
  /**
   * Public class with multiple annotations - should be preserved with annotations.
   */

  var data: String = "public"

  @Logged
  def processData(): String = {
    data.toUpperCase
  }

  // … method omitted (4 lines)
}

// … function omitted (8 lines)

@Logged
@Validate
def publicAnnotatedFunction(data: String): String = {
  /**
   * Public function with annotations - should preserve function and annotations.
   */
  data.toUpperCase
}

// Class with mixed annotated members
class MixedAnnotatedClass {
  @Logged
  def publicAnnotatedMethod(): Unit = {
    // Public method with annotation - should preserve both
  }

  // … 2 methods omitted (9 lines)
}

// … class omitted (13 lines)

@Logged
@Validate
class PublicMultiAnnotatedClass {
  /**
   * Public class with multiple annotations - should preserve class and all annotations.
   */

  @Logged
  @Validate
  def multiAnnotatedMethod(): Unit = {
    // Multiple annotations on public method - should preserve all
  }
}
