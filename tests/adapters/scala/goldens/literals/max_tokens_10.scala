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

  val TEMPLATE_WITH_DATA = s"""
User Information:
- Name…""" // literal string (−63 tokens)
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
    "…" -> "…") // literal array (−7 tokens)

  private val largeConfig = Map("…" -> "…") // literal array (−329 tokens)

  private val supportedLanguages: List[String] = List(
    "english",
    "spanish",
    "…") // literal array (−91 tokens)

  private val allowedExtensions: Set[String] = Set(
    ".scala",
    ".sc",
    "…") // literal array (−49 tokens)

  def processData(): DataContainer = {
    // Function with various literal data
    val smallArray = List("one", "two", "three")

    val largeArray = List(
      "item_001",
      "…") // literal array (−148 tokens)

    val nestedData = Map("…" -> "…") // literal array (−200 tokens)

    DataContainer(
      tags = smallArray,
      items = largeArray,
      metadata = Map("type" -> "test", "…" -> "…"), // literal array (−2 tokens)
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
    "…" -> "…") // literal array (−4 tokens)
}

object LargeConstants {
  val HTTP_STATUS_CODES = Map(
    "CONTINUE" -> 100,
    "…" -> "…") // literal array (−396 tokens)

  val ERROR_MESSAGES = Map("…" -> "…") // literal array (−127 tokens)
}
