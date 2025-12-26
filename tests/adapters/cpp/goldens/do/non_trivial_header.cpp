/**
 * Utils header with class definitions.
 */

#ifndef UTILS_HPP
#define UTILS_HPP

#include <string>

namespace utils {

class Config {
public:
    int value;
    std::string name;

    void initialize();
};

} // namespace utils

#endif // UTILS_HPP
