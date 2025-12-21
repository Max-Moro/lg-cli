
public class Calculator {
    private List<String> history = new ArrayList<>();

    public Calculator(String name) {
        this.name = name;
        this.history = new ArrayList<>();
    }

    public int add(int a, int b) {
        // … method body omitted (3 lines)
    }

    public List<String> getHistory() {
        return new ArrayList<>(history);
    }
}
