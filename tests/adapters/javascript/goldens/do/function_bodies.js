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
        this.history.push(`add(${a}, ${b}) = ${result}`);
        console.log(`Addition result: ${result}`);
        return result;
    }

    multiply(a, b) {
        const result = a * b;
        this.history.push(`multiply(${a}, ${b}) = ${result}`);
        return result;
    }

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

export function processUserData(users) {
    const result = { valid: [], invalid: [] };

    for (const user of users) {
        if (user.id > 0 && user.name && user.email.includes('@')) {
            result.valid.push(user);
        } else {
            result.invalid.push(user);
        }
    }

    return result;
}

// Arrow functions for testing different function types
const simpleArrow = () => "simple";

const complexArrow = (data) => {
    const processed = data
        .filter(item => item.length > 0)
        .map(item => item.trim())
        .sort();

    return processed.join(', ');
};

const asyncArrow = async (url) => {
    try {
        const response = await fetch(url);
        const data = await response.json();

        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }

        return data;
    } catch (error) {
        console.error('Fetch error:', error);
        throw error;
    }
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
    } else {
        return value * 2;
    }
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
        try {
            const processed = processor(item);
            result.push(processed);
        } catch (error) {
            console.warn('Processing failed for item:', item);
        }
    }

    return result;
}

// Default export function
export default function main() {
    const calc = new Calculator("test");
    console.log(calc.add(2, 3));
    console.log(calc.multiply(4, 5));

    const users = [
        { id: 1, name: "Alice", email: "alice@example.com" },
        { id: 2, name: "Bob", email: "bob@example.com" }
    ];

    const processed = processUserData(users);
    console.log(processed);
}
