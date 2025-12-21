/**
 * Scala module for testing public API filtering.
 */

package com.example.publicapi

import java.time.Instant

// Public module-level constants (should be preserved)
object PublicConstants {
  val PUBLIC_VERSION = "1.0.0"
  val API_ENDPOINT = "https://api.example.com"

  // Private constants (should be filtered out)
  // … 2 vals omitted
}

// Public case class (should be preserved)
case class User(
  id: Long,
  name: String,
  email: String,
  createdAt: Instant
)

// Private case class (should be filtered out)
// … class omitted (4 lines)

// Public type alias (should be preserved)
type UserRole = String

// Public class with mixed visibility members
class UserManager(private val apiEndpoint: String = PublicConstants.API_ENDPOINT) {
  // Public properties
  val version: String = PublicConstants.PUBLIC_VERSION
  var isInitialized: Boolean = false

  // Private properties (should be filtered out with public_api_only)
  // … 2 vals omitted (3 lines)

  // Protected properties (should be filtered out)
  // … val omitted (2 lines)

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

  // Private methods (should be filtered out)
  // … 4 methods omitted (26 lines)

  // Protected methods (should be filtered out)
  // … 2 methods omitted (7 lines)

  // Public property with getter
  def userCount: Int = internalCache.size

  // Private property with getter (should be filtered out)
  // … method omitted (4 lines)
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

  // Private static methods (should be filtered out)
  // … method omitted (3 lines)
}

// Private class (should be filtered out)
// … class omitted (11 lines)

// Public abstract class (should be preserved)
abstract class BaseService {
  protected def serviceName: String

  def initialize(): Unit

  def getServiceInfo: Map[String, String] = Map(
    "name" -> serviceName,
    "version" -> PublicConstants.PUBLIC_VERSION
  )

  // Protected abstract method (should be filtered out in public API)
  // … method omitted
}

// Public trait (should be preserved)
trait UserService {
  def findById(id: Long): Option[User]
  def save(user: User): User
}

// Private trait (should be filtered out)
// … trait omitted (4 lines)

// Public sealed trait with case objects (should be preserved)
sealed trait UserStatus
object UserStatus {
  case object Active extends UserStatus
  case object Inactive extends UserStatus
  case object Pending extends UserStatus
  case object Banned extends UserStatus
}

// Private sealed trait (should be filtered out)
// … trait omitted
// … object omitted (5 lines)

// Public functions (should be preserved)
def createUserManager(endpoint: Option[String] = None): UserManager = {
  new UserManager(endpoint.getOrElse(PublicConstants.API_ENDPOINT))
}

def isValidUserRole(role: Any): Boolean = {
  UserManager.validateUserRole(role.toString)
}

// Private functions (should be filtered out)
// … 2 functions omitted (7 lines)

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

  // Private object member (should be filtered out)
  // … method omitted (3 lines)
}

// Private object (should be filtered out)
// … object omitted (14 lines)

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

// Annotated functions
// … function omitted (7 lines)

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

// Multiple stacked annotations on private elements
// … class omitted (12 lines)

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
