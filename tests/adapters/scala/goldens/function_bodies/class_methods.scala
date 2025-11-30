
class Calculator(val name: String) {
  private val history = scala.collection.mutable.ListBuffer.empty[String]

  def add(a: Int, b: Int): Int = // … method body omitted (5 lines)

  def getHistory: List[String] = history.toList
}
