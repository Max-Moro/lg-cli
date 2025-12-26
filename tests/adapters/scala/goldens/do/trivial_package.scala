/**
 * Utility package for data processing.
 */
package com.example

import scala.util._
import java.time._

package object utils {
  // Only type aliases and re-exports
  type Result[A] = Either[Throwable, A]
}
