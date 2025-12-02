/**
 * Scala module for testing literal optimization.
 */

package com.example.literals

// Short string literal (should be preserved)
object Constants {
  val SHORT_MESSAGE = "Hello, World!"

  // Long string literal (candidate for trimming)
  val LONG_MESSAGE = """This is an extremely long message that cont…""" // literal string (−62 tokens)

  // Multi-line string with interpolation
  def getUserName(): String = "John Doe"
  def getUserEmail(): String = "john.doe@example.com"
  def getAccountStatus(): String = "active"
  def getPermissions(): List[String] = List("read", "write", "admin")
  def getLastLogin(): String = "2024-01-15T1…" // literal string (−5 tokens)
  def getProfileCompleteness(): Int = 85

  val TEMPLATE_WITH_DATA = "s"""
User Information:
- Name: ${…" // literal string (−62 tokens)
}

case class DataContainer(
  // Small array (should be preserved)
  tags: List[String],

  // Large array (candidate for trimming)
  items: List[String],

  // Small object (should be preserved)
  metadata: Map[String, Any],

  // Large object (candidate for trimming)
  configuration: Map[String, Any]
)

class LiteralDataManager {
  // Class properties with various literal types
  private val smallConfig = Map(
    "debug" -> true,
    "version" -> "1.0.0"
  )

  private val largeConfig = Map(
    "database" -> Map(
      "host" -> "localhost",
      "port" -> 5432,
      "name" -> "application_db",
      "ssl" -> false,
      "pool" -> Map(
        "min" -> 2,
        "max" -> 10,
        "idleTimeoutMillis" -> 30000,
        "connectionTimeoutMillis" -> 2000
      ),
      "retry" -> Map(
        "attempts" -> 3,
        "delay" -> 1000,
        "backoff" -> "exponential"
      )
    ),
    "cache" -> Map(
      "redis" -> Map(
        "host" -> "localhost",
        "port" -> 6379,
        "db" -> 0,
        "ttl" -> 3600
      ),
      "memory" -> Map(
        "maxSize" -> 1000,
        "ttl" -> 1800
      )
    ),
    "api" -> Map(
      "baseUrl" -> "https://api.example.com",
      "timeout" -> 30000,
      "retries" -> 3,
      "rateLimit" -> Map(
        "requests" -> 100,
        "window" -> 60000
      )
    ),
    "features" -> Map(
      "authentication" -> true,
      "authorization" -> true,
      "logging" -> true,
      "monitoring" -> true,
      "analytics" -> false,
      "caching" -> true,
      "compression" -> true
    )
  )

  private val supportedLanguages: List[String] = List(
    "english", "spanish", "french", "german", "italian", "portuguese",
    "russian", "chinese", "japanese", "korean", "arabic", "hindi",
    "dutch", "swedish", "norwegian", "danish", "finnish", "polish",
    "czech", "hungarian", "romanian", "bulgarian", "croatian", "serbian"
  )

  private val allowedExtensions: Set[String] = Set(
    ".scala", ".sc", ".java", ".kt",
    ".py", ".js", ".ts", ".jsx", ".tsx",
    ".c", ".cpp", ".cs", ".go", ".rs",
    ".php", ".rb", ".swift", ".clj"
  )

  def processData(): DataContainer = {
    // Function with various literal data
    val smallArray = List("one", "two", "three")

    val largeArray = List(
      "item_001", "item_002", "item_003", "item_004", "item_005",
      "item_006", "item_007", "item_008", "item_009", "item_010",
      "item_011", "item_012", "item_013", "item_014", "item_015",
      "item_016", "item_017", "item_018", "item_019", "item_020",
      "item_021", "item_022", "item_023", "item_024", "item_025",
      "item_026", "item_027", "item_028", "item_029", "item_030"
    )

    val nestedData = Map(
      "level1" -> Map(
        "level2" -> Map(
          "level3" -> Map(
            "data" -> List(
              Map("id" -> 1, "name" -> "First", "active" -> true),
              Map("id" -> 2, "name" -> "Second", "active" -> false),
              Map("id" -> 3, "name" -> "Third", "active" -> true),
              Map("id" -> 4, "name" -> "Fourth", "active" -> true),
              Map("id" -> 5, "name" -> "Fifth", "active" -> false)
            ),
            "metadata" -> Map(
              "created" -> "2024-01-01",
              "updated" -> "2024-01-15",
              "version" -> 3,
              "checksum" -> "abcdef123456"
            )
          )
        )
      )
    )

    DataContainer(
      tags = smallArray,
      items = largeArray,
      metadata = Map("type" -> "test", "count" -> smallArray.size),
      configuration = nestedData
    )
  }

  def getLongQuery(): String = {
    // Very long SQL-like query string
    """
      SELECT
        users.id, use…""" /* literal string (−177 tokens) */.stripMargin
  }
}

// Module-level constants with different sizes
object SmallConstants {
  val VALUES = Map(
    "API_VERSION" -> "v1",
    "DEFAULT_LIMIT" -> 50
  )
}

object LargeConstants {
  val HTTP_STATUS_CODES = Map(
    "CONTINUE" -> 100,
    "SWITCHING_PROTOCOLS" -> 101,
    "OK" -> 200,
    "CREATED" -> 201,
    "ACCEPTED" -> 202,
    "NON_AUTHORITATIVE_INFORMATION" -> 203,
    "NO_CONTENT" -> 204,
    "RESET_CONTENT" -> 205,
    "PARTIAL_CONTENT" -> 206,
    "MULTIPLE_CHOICES" -> 300,
    "MOVED_PERMANENTLY" -> 301,
    "FOUND" -> 302,
    "SEE_OTHER" -> 303,
    "NOT_MODIFIED" -> 304,
    "USE_PROXY" -> 305,
    "TEMPORARY_REDIRECT" -> 307,
    "PERMANENT_REDIRECT" -> 308,
    "BAD_REQUEST" -> 400,
    "UNAUTHORIZED" -> 401,
    "PAYMENT_REQUIRED" -> 402,
    "FORBIDDEN" -> 403,
    "NOT_FOUND" -> 404,
    "METHOD_NOT_ALLOWED" -> 405,
    "NOT_ACCEPTABLE" -> 406,
    "PROXY_AUTHENTICATION_REQUIRED" -> 407,
    "REQUEST_TIMEOUT" -> 408,
    "CONFLICT" -> 409,
    "GONE" -> 410,
    "LENGTH_REQUIRED" -> 411,
    "PRECONDITION_FAILED" -> 412,
    "PAYLOAD_TOO_LARGE" -> 413,
    "URI_TOO_LONG" -> 414,
    "UNSUPPORTED_MEDIA_TYPE" -> 415,
    "RANGE_NOT_SATISFIABLE" -> 416,
    "EXPECTATION_FAILED" -> 417,
    "INTERNAL_SERVER_ERROR" -> 500,
    "NOT_IMPLEMENTED" -> 501,
    "BAD_GATEWAY" -> 502,
    "SERVICE_UNAVAILABLE" -> 503,
    "GATEWAY_TIMEOUT" -> 504,
    "HTTP_VERSION_NOT_SUPPORTED" -> 505
  )

  val ERROR_MESSAGES = Map(
    "VALIDATION_FAILED" -> "Input validation failed. Please check you…", // literal string (−4 tokens)
    "AUTHENTICATION_REQUIRED" -> "Authentication is required to access this resource.",
    "AUTHORIZATION_FAILED" -> "You do not have permission to perform this action.",
    "RESOURCE_NOT_FOUND" -> "The requested resource could not be foun…", // literal string (−2 tokens)
    "INTERNAL_ERROR" -> "An internal server error occurred. Please…", // literal string (−3 tokens)
    "RATE_LIMIT_EXCEEDED" -> "Rate limit exceeded. Please wait before makin…", // literal string (−1 tokens)
    "INVALID_REQUEST_FORMAT" -> "The request format is invalid. Please check t…" // literal string (−1 tokens)
  )
}
