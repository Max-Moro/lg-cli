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
        history.push_back("add(" + std::to_string(a) + ", " + std::to_string(b) + ") = " + std::to_string(result));
        std::cout << "Addition result: " << result << std::endl;
        return result;
    }

    int multiply(int a, int b) {
        int result = a * b;
        history.push_back("multiply(" + std::to_string(a) + ", " + std::to_string(b) + ") = " + std::to_string(result));
        return result;
    }

    std::vector<std::string> getHistory() const {
        return history;
    }

private:
    bool validateInput(int value) {
        std::string str = std::to_string(value);

        for (char c : str) {
            if (c != '-' && (c < '0' || c > '9')) {
                std::cerr << "Input must be a number" << std::endl;
                return false;
            }
        }

        if (value == INT_MAX || value == INT_MIN) {
            std::cerr << "Input must be finite" << std::endl;
            return false;
        }

        return true;
    }
};

ProcessingResult processUserData(const std::vector<User>& users) {
    ProcessingResult result;

    for (const auto& user : users) {
        if (user.id > 0 &&
            !user.name.empty() &&
            user.email.find('@') != std::string::npos) {
            result.valid.push_back(user);
        } else {
            result.invalid.push_back(user);
        }
    }

    return result;
}

// Template function
template<typename T, typename Processor>
std::vector<T> processArray(const std::vector<T>& items, Processor processor) {
    std::vector<T> result;

    for (const auto& item : items) {
        try {
            result.push_back(processor(item));
        } catch (const std::exception& error) {
            std::cerr << "Processing failed for item" << std::endl;
        }
    }

    return result;
}

// Lambda usage function
std::vector<int> filterPositive(const std::vector<int>& numbers) {
    std::vector<int> result;
    std::copy_if(numbers.begin(), numbers.end(), std::back_inserter(result),
                 [](int n) { return n > 0; });
    return result;
}

int main() {
    Calculator calc("test");
    std::cout << calc.add(2, 3) << std::endl;
    std::cout << calc.multiply(4, 5) << std::endl;

    std::vector<User> users = {
        {1, "Alice", "alice@example.com"},
        {2, "Bob", "bob@example.com"}
    };

    ProcessingResult processed = processUserData(users);
    std::cout << "Valid users: " << processed.valid.size() << std::endl;

    return 0;
}
