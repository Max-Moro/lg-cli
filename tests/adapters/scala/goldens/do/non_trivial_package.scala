/**
 * Utility package for data processing.
 */
package com.example

import scala.util._

package object utils {
  type Result[A] = Either[Throwable, A]

  def initialize(): Boolean = true
}
