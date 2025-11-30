/**
 * C++ module for testing function body optimization.
 */

#include <iostream>
#include <vector>
#include <string>
#include <algorithm>

struct User {
    int id;
    std::string name;
    std::string email;
};

struct ProcessingResult {
    std::vector<User> valid;
    std::vector<User> invalid;
};

class Calculator {
private:
    std::vector<std::string> history;
    std::string name;

public:
    Calculator() : Calculator("default") {}

    Calculator(const std::string& name) : name(name) {
        history.reserve(10);
    }

    int add(int a, int b) // … method body omitted (6 lines)

    int multiply(int a, int b) // … method body omitted (5 lines)

    std::vector<std::string> getHistory() const {
        return history;
    }

private:
    bool validateInput(int value) // … method body omitted (17 lines)
};

ProcessingResult processUserData(const std::vector<User>& users) // … function body omitted (15 lines)

// Template function
template<typename T, typename Processor>
std::vector<T> processArray(const std::vector<T>& items, Processor processor) // … function body omitted (13 lines)

// Lambda usage function
std::vector<int> filterPositive(const std::vector<int>& numbers) // … function body omitted (6 lines)

int main() // … function body omitted (15 lines)
