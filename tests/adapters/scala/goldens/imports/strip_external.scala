/**
 * Scala module for testing import optimization.
 */

package com.example.imports

// … 32 imports omitted (27 lines)

// Local/relative imports (should be considered local)
import com.example.imports.services.UserService
import com.example.imports.database.DatabaseConnection
import com.example.imports.errors.{ValidationError, NetworkError}
import com.example.imports.utils.helpers.{formatDate, parseJson}
import com.example.imports.types.{ApiResponse, UserModel, PostModel}

// Imports from different package levels
import com.example.shared.SharedUtility
import com.example.core.CoreModule
import com.example.config.AppConfig

// Import with aliasing
import com.example.imports.utils.logger.{Logger => AppLogger}
import com.example.imports.config.{Config => AppConfig2}
import com.example.imports.http.{HttpClient => CustomHttpClient}

// Wildcard imports
import com.example.imports.extensions._
import com.example.imports.constants._

// Long import lists from single package (candidates for summarization)
import spray.json.DefaultJsonProtocol._
import spray.json._
import spray.json.{JsValue, JsObject, JsArray, JsString, JsNumber, JsBoolean, JsNull}

// … 9 imports omitted (5 lines)

// Local imports with long lists
import com.example.imports.services.{
  createUser,
  updateUser,
  deleteUser,
  getUserById,
  getUserByEmail,
  getUsersByRole,
  getUsersWithPagination,
  activateUser,
  deactivateUser,
  resetUserPassword,
  changeUserRole,
  validateUserPermissions
}

import com.example.utils.validation.{
  validateEmail,
  validatePassword,
  validatePhoneNumber,
  validatePostalCode,
  validateCreditCard,
  sanitizeInput,
  formatCurrency,
  formatPhoneNumber,
  generateSlug,
  createHash,
  verifyHash
}

class ImportTestService(
  userService: UserService,
  dbConnection: DatabaseConnection,
  logger: AppLogger
)(implicit ec: ExecutionContext) {

  def processData(data: List[Any]): Future[ApiResponse[List[Any]]] = {
    // Using external libraries
    val processed = data.map { item =>
      Map(
        "id" -> UUID.randomUUID(),
        "timestamp" -> Instant.now().toString,
        "item" -> item
      )
    }

    // Using local utilities
    val validated = processed.filter { item =>
      item.get("email")
        .map(_.toString)
        .exists(validateEmail)
    }

    // Using Scala standard library
    val filePath = "output.json"

    Future.successful(
      ApiResponse(
        success = true,
        data = validated,
        timestamp = formatDate(LocalDateTime.now())
      )
    )
  }

  def makeHttpRequest(url: String)(implicit system: ActorSystem): Future[String] = {
    import system.dispatcher

    // Using Akka HTTP
    val request = HttpRequest(uri = url)
      .withHeaders(
        headers.`User-Agent`("ImportTestService/1.0")
      )

    Http()
      .singleRequest(request)
      .flatMap { response =>
        Unmarshal(response.entity).to[String]
      }
      .recover {
        case e: Exception =>
          logger.error("HTTP request failed", e)
          throw new NetworkError("Request failed")
      }
  }

  def serializeData(data: Any): String = {
    // Using Play JSON
    val json = Json.toJson(data)
    Json.prettyPrint(json)
  }
}

// Case class with validation annotations
case class ValidatedUser(
  id: String,
  name: String,
  email: String,
  age: Option[Int],
  phone: Option[String]
)

// Akka HTTP route
trait UserRoutes {
  implicit def system: ActorSystem
  implicit def executionContext: ExecutionContext

  val userRoute: Route =
    pathPrefix("api" / "users") {
      concat(
        path(LongNumber) { id =>
          get {
            complete(s"Get user $id")
          }
        },
        pathEnd {
          post {
            entity(as[ValidatedUser]) { user =>
              complete(StatusCodes.Created, user)
            }
          }
        }
      )
    }
}

// Play JSON format
object UserFormats {
  implicit val userFormat: Format[ValidatedUser] = Json.format[ValidatedUser]
}

// Slick database query
class UserTable(tag: Tag) extends Table[ValidatedUser](tag, "users") {
  def id = column[String]("id", O.PrimaryKey)
  def name = column[String]("name")
  def email = column[String]("email")
  def age = column[Option[Int]]("age")
  def phone = column[Option[String]]("phone")

  def * = (id, name, email, age, phone).mapTo[ValidatedUser]
}

// Cats Effect IO
object CatsEffectExample {
  def processWithIO(items: List[String]): IO[List[String]] =
    items.traverse { item =>
      IO.sleep(100.millis) *>
        IO.pure(item.toUpperCase)
    }
}

// Default export
object Main extends App {
  implicit val system: ActorSystem = ActorSystem("ImportTestSystem")
  implicit val ec: ExecutionContext = system.dispatcher

  val config = ConfigFactory.load()
  println(s"Application started with config: ${config.getString("app.name")}")
}
