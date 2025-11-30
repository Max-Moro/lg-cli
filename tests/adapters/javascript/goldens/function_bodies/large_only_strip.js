/**
 * JavaScript module for testing function body optimization.
 */

class Calculator {
    constructor(name = "default") // … method body omitted (4 lines)

    add(a, b) // … method body omitted (6 lines)

    multiply(a, b) // … method body omitted (5 lines)

    getHistory() {
        return [...this.history];
    }

    #validateInput(value) {
        if (typeof value !== 'number') {
            throw new Error('Input must be a number');
        }

        if (!isFinite(value)) {
            throw new Error('Input must be finite');
        }

        return true;
    }
}

export function processUserData(users) // … function body omitted (13 lines)

// Arrow functions for testing different function types
const simpleArrow = () => "simple";

const complexArrow = (data) => // … arrow_function_body omitted (8 lines);

const asyncArrow = async (url) => // … arrow_function_body omitted (15 lines);

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
function overloadedFunction(value) // … function body omitted (7 lines)

// Generic function (via JSDoc)
/**
 * @template T
 * @param {T[]} items
 * @param {(item: T) => T} processor
 * @returns {T[]}
 */
function processArray(items, processor) // … function body omitted (14 lines)

// Default export function
export default function main() // … function body omitted (13 lines)
