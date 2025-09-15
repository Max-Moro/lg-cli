/**
 * TypeScript module for testing function body optimization.
 */

import { Observable } from "rxjs";

interface User {
    id: number;
    name: string;
    email: string;
}

class Calculator {
    private history: string[] = [];
    
    constructor(name: string = "default") {
        this.name = name;
        this.history = [];
    }
    
    public add(a: number, b: number): number {
        const result = a + b;
        this.history.push(`add(${a}, ${b}) = ${result}`);
        console.log(`Addition result: ${result}`);
        return result;
    }
    
    public multiply(a: number, b: number): number {
        const result = a * b;
        this.history.push(`multiply(${a}, ${b}) = ${result}`);
        return result;
    }
    
    public getHistory(): string[] {
        return [...this.history];
    }
    
    private validateInput(value: number): boolean {
        if (typeof value !== 'number') {
            throw new Error('Input must be a number');
        }
        
        if (!isFinite(value)) {
            throw new Error('Input must be finite');
        }
        
        return true;
    }
}

export function processUserData(users: User[]): { valid: User[], invalid: User[] } {
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

const complexArrow = (data: string[]) => {
    const processed = data
        .filter(item => item.length > 0)
        .map(item => item.trim())
        .sort();
    
    return processed.join(', ');
};

const asyncArrow = async (url: string): Promise<any> => {
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

// Function with multiple overloads
function overloadedFunction(value: string): string;
function overloadedFunction(value: number): number;
function overloadedFunction(value: string | number): string | number {
    if (typeof value === 'string') {
        return value.toUpperCase();
    } else {
        return value * 2;
    }
}

// Generic function
function processArray<T>(items: T[], processor: (item: T) => T): T[] {
    const result: T[] = [];
    
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
export default function main(): void {
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