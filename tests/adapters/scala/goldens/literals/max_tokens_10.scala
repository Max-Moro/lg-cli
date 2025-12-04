/**
 * Scala module for testing literal optimization.
 */

package com.example.literals

// Short string literal (should be preserved)
object Constants {
  val SHORT_MESSAGE = "Hello, World!"

  // Long string literal (candidate for trimming)
  val LONG_MESSAGE = """This is an extremely long message that cont…""" // literal string (−65 tokens)

  // Multi-line string with interpolation
  def getUserName(): String = "John Doe"
  def getUserEmail(): String = "john.doe@example.com"
  def getAccountStatus(): String = "active"
  def getPermissions(): List[String] = List("read", "write", "admin")
  def getLastLogin(): String = "2024-01-15T1…" // literal string (−7 tokens)
  def getProfileCompleteness(): Int = 85

  val TEMPLATE_WITH_DATA = s"""
User Inform…""" // literal string (−69 tokens)
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
    // … (1 more, −11 tokens)
  )

  private val largeConfig = Map(
    "database" -> Map(
        "host" -> "localhost",
        // … (5 more, −101 tokens)
    ),
    // … (3 more, −304 tokens)
  )

  private val supportedLanguages: List[String] = List(
    "english",
    "spanish"
    // … (22 more, −85 tokens)
  )

  private val allowedExtensions: Set[String] = Set(
    ".scala",
    ".sc"
    // … (16 more, −49 tokens)
  )

  def processData(): DataContainer = {
    // Function with various literal data
    val smallArray = List("one", "two", "three")

    val largeArray = List(
      "item_001"
      // … (29 more, −145 tokens)
    )

    val nestedData = Map(
      "level1" -> Map(
          "level2" -> Map(
              "level3" -> Map(
                  "data" -> List(
                      Map("id" -> 1, "name" -> "First", "active" -> true),
                      // … (4 more, −85 tokens)
                  ),
                  // … (1 more, −137 tokens)
              ),
          ),
      ),
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
      SELECT…""" /* literal string (−185 tokens) */.stripMargin
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
    // … (40 more, −319 tokens)
  )

  val ERROR_MESSAGES = Map(
    "VALIDATION_FAILED" -> "Input validation failed. Please check you…" // literal string (−6 tokens),
    // … (6 more, −104 tokens)
  )
}
