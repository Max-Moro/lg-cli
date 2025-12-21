/**
 * JavaScript module for testing function body optimization.
 */

class Calculator {
    constructor(name = "default") {
        this.name = name;
        this.history = [];
    }

    add(a, b) {
        const result = a + b;
        // … method body truncated (2 lines)
        return result;
    }

    multiply(a, b) {
        const result = a * b;
        // … method body truncated
        return result;
    }

    getHistory() {
        return [...this.history];
    }

    #validateInput(value) {
        if (typeof value !== 'number') {
        // … method body truncated (7 lines)

        return true;
    }
}

export function processUserData(users) {
    const result = { valid: [], invalid: [] };

    // … function body truncated (8 lines)

    return result;
}

// Arrow functions for testing different function types
const simpleArrow = () => "simple";

const complexArrow = (data) => {
    const processed = data
    // … arrow function body truncated (4 lines)

    return processed.join(', ');
};

const asyncArrow = async (url) => {
    try {
        const response = await fetch(url);
    // … arrow function body truncated (11 lines)
};

// Function with multiple overloads (via JSDoc)
/**
 * @overload
 * @param {string} value
 * @returns {string}
 */
/**
 * @overload
 * @param {number} value
 * @returns {number}
 */
function overloadedFunction(value) {
    if (typeof value === 'string') {
        return value.toUpperCase();
    // … function body truncated (3 lines)
}

// Generic function (via JSDoc)
/**
 * @template T
 * @param {T[]} items
 * @param {(item: T) => T} processor
 * @returns {T[]}
 */
function processArray(items, processor) {
    const result = [];

    for (const item of items) {
    // … function body truncated (8 lines)

    return result;
}

// Default export function
export default function main() {
    const calc = new Calculator("test");
    // … function body truncated (10 lines)
}
