/**
 * JavaScript module for testing function body optimization.
 */

class Calculator {
    constructor(name = "default") {
        // … method body omitted (2 lines)
    }

    add(a, b) {
        // … method body omitted (4 lines)
    }

    multiply(a, b) {
        // … method body omitted (3 lines)
    }

    getHistory() {
        return [...this.history];
    }

    #validateInput(value) {
        // … method body omitted (7 lines)
    }
}

export function processUserData(users) {
    // … function body omitted (9 lines)
}

// Arrow functions for testing different function types
const simpleArrow = () => "simple";

const complexArrow = (data) => {
    // … arrow function body omitted (5 lines)
};

const asyncArrow = async (url) => {
    // … arrow function body omitted (11 lines)
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
    // … function body omitted (5 lines)
}

// Generic function (via JSDoc)
/**
 * @template T
 * @param {T[]} items
 * @param {(item: T) => T} processor
 * @returns {T[]}
 */
function processArray(items, processor) {
    // … function body omitted (10 lines)
}

// Default export function
export default function main() {
    // … function body omitted (9 lines)
}
