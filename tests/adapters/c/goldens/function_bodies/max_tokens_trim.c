/**
 * C module for testing function body optimization.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    int id;
    char name[50];
    char email[100];
} User;

typedef struct {
    User* valid;
    User* invalid;
    int valid_count;
    int invalid_count;
} ProcessingResult;

typedef struct {
    char** history;
    int history_count;
    int history_capacity;
    char name[50];
} Calculator;

Calculator* calculator_new(const char* name) {
    // … function body truncated (10 lines)

    return calc;
}

void calculator_free(Calculator* calc) {
    if (!calc) return;

    // … function body truncated (5 lines)
}

int calculator_add(Calculator* calc, int a, int b) {
    if (!calc) return 0;

    int result = a + b;

    // … function body truncated (12 lines)

    return result;
}

int calculator_multiply(Calculator* calc, int a, int b) {
    if (!calc) return 0;

    int result = a * b;

    // … function body truncated (11 lines)

    return result;
}

char** calculator_get_history(Calculator* calc, int* count) {
    if (!calc || !count) {
    // … function body truncated (11 lines)

    return copy;
}

static int validate_input(int value) {
    char buffer[20];
    // … function body truncated (14 lines)

    return 1;
}

ProcessingResult* process_user_data(User* users, int count) {
    // … function body truncated (18 lines)

    return result;
}

void free_processing_result(ProcessingResult* result) {
    if (!result) return;
    free(result->valid);
    // … function body truncated (2 lines)
}

typedef void (*ItemProcessor)(void* item);

void** process_array(void** items, int count, ItemProcessor processor) {
    // … function body truncated (10 lines)

    return result;
}

int main(void) {
    Calculator* calc = calculator_new("test");
    // … function body truncated (19 lines)

    return 0;
}
