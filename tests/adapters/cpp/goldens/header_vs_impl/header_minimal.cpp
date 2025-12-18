#ifndef MYLIB_HPP
#define MYLIB_HPP

#include <iostream>
#include <vector>
#include "utils.hpp"

/**
 * Calculate sum of two numbers.
 */
int calculateSum(int a, int b);

/**
 * Internal helper function.
 */
static inline int helper(int x) {
    return x * 2;
}

struct Data {
    int id;
    std::string name;
};

#endif // … comment omitted
