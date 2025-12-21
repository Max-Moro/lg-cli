
class Calculator(private val name: String) {
    private val history: MutableList<String> = mutableListOf()
    
    fun add(a: Int, b: Int): Int {
        // … method body omitted (3 lines)
    }
    
    fun getHistory(): List<String> {
        return history.toList()
    }
}
