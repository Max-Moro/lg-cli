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
  private val smallConfig = [M, "…"] // literal array (−18 tokens)

  private val largeConfig = [M, "…"] // literal array (−331 tokens)

  private val supportedLanguages: List[String] = [L, "…"] // literal array (−101 tokens)

  private val allowedExtensions: Set[String] = [S, "…"] // literal array (−58 tokens)

  def processData(): DataContainer = {
    // Function with various literal data
    val smallArray = List("one", "two", "three")

    val largeArray = [L, "…"] // literal array (−155 tokens)

    val nestedData = [M, "…"] // literal array (−202 tokens)

    DataContainer(
      tags = smallArray,
      items = largeArray,
      metadata = [M, "…"], // literal array (−11 tokens)
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
  val VALUES = [M, "…"] // literal array (−18 tokens)
}

object LargeConstants {
  val HTTP_STATUS_CODES = [M, "…"] // literal array (−409 tokens)

  val ERROR_MESSAGES = [M, "…"] // literal array (−129 tokens)
}
