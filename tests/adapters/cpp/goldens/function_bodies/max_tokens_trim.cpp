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

    int add(int a, int b) {
        int result = a + b;
    int add(int a, int b) // … method body omitted (4 lines)

    int multiply(int a, int b) {
        int result = a * b;
    int multiply(int a, int b) // … method body omitted (3 lines)

    std::vector<std::string> getHistory() const {
        return history;
    }

private:
    bool validateInput(int value) {
        std::string str = std::to_string(value);

    bool validateInput(int value) // … method body omitted (14 lines)
};

ProcessingResult processUserData(const std::vector<User>& users) {
    ProcessingResult result;

    for (const auto& user : users) {
ProcessingResult processUserData(const std::vector<User>& users) // … function body omitted (11 lines)

// Template function
template<typename T, typename Processor>
std::vector<T> processArray(const std::vector<T>& items, Processor processor) {
    std::vector<T> result;

    for (const auto& item : items) {
std::vector<T> processArray(const std::vector<T>& items, Processor processor) // … function body omitted (9 lines)

// Lambda usage function
std::vector<int> filterPositive(const std::vector<int>& numbers) {
    std::vector<int> result;
std::vector<int> filterPositive(const std::vector<int>& numbers) // … function body omitted (4 lines)

int main() {
    Calculator calc("test");
int main() // … function body omitted (13 lines)
