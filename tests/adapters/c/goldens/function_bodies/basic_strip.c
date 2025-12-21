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
    // … function body omitted (8 lines)
}

void calculator_free(Calculator* calc) {
    // … function body omitted (6 lines)
}

int calculator_add(Calculator* calc, int a, int b) {
    // … function body omitted (12 lines)
}

int calculator_multiply(Calculator* calc, int a, int b) {
    // … function body omitted (11 lines)
}

char** calculator_get_history(Calculator* calc, int* count) {
    // … function body omitted (10 lines)
}

static int validate_input(int value) {
    // … function body omitted (13 lines)
}

ProcessingResult* process_user_data(User* users, int count) {
    // … function body omitted (16 lines)
}

void free_processing_result(ProcessingResult* result) {
    // … function body omitted (4 lines)
}

typedef void (*ItemProcessor)(void* item);

void** process_array(void** items, int count, ItemProcessor processor) {
    // … function body omitted (9 lines)
}

int main(void) {
    // … function body omitted (16 lines)
}
