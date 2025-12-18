#ifndef MYLIB_H
#define MYLIB_H

#include <stdio.h>
#include "utils.h"

/**
 * Calculate sum of two numbers.
 */
int calculate_sum(int a, int b);

/**
 * Internal helper function.
 */
static inline int helper(int x) {
    return x * 2;
}

typedef struct {
    int id;
    char name[50];
} Data;

#endif // … comment omitted
