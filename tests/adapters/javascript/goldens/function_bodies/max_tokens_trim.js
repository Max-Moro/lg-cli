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
    add(a, b) // … method body omitted (4 lines)

    multiply(a, b) {
        const result = a * b;
    multiply(a, b) // … method body omitted (3 lines)

    getHistory() {
        return [...this.history];
    }

    #validateInput(value) {
        if (typeof value !== 'number') {
    #validateInput(value) // … method body omitted (9 lines)
}

export function processUserData(users) {
    const result = { valid: [], invalid: [] };

export function processUserData(users) // … function body omitted (10 lines)

// Arrow functions for testing different function types
const simpleArrow = () => "simple";

const complexArrow = (data) => {
    const processed = data
        .filter(item => item.length > 0)
const complexArrow = (data) => // … arrow_function_body omitted (5 lines);

const asyncArrow = async (url) => {
    try {
        const response = await fetch(url);
const asyncArrow = async (url) => // … arrow_function_body omitted (12 lines);

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
function overloadedFunction(value) // … function body omitted (4 lines)

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
function processArray(items, processor) // … function body omitted (9 lines)

// Default export function
export default function main() {
    const calc = new Calculator("test");
export default function main() // … function body omitted (11 lines)
