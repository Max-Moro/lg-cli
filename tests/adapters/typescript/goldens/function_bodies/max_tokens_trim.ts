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
        // … method body truncated (2 lines)
        return result;
    }
    
    public multiply(a: number, b: number): number {
        const result = a * b;
        // … method body truncated
        return result;
    }
    
    public getHistory(): string[] {
        return [...this.history];
    }
    
    private validateInput(value: number): boolean {
        if (typeof value !== 'number') {
        // … method body truncated (7 lines)
        
        return true;
    }
}

export function processUserData(users: User[]): { valid: User[], invalid: User[] } {
    const result = { valid: [], invalid: [] };
    
    // … function body truncated (8 lines)
    
    return result;
}

// Arrow functions for testing different function types
const simpleArrow = () => "simple";

const complexArrow = (data: string[]) => {
    const processed = data
    // … function body truncated (4 lines)
    
    return processed.join(', ');
};

const asyncArrow = async (url: string): Promise<any> => {
    try {
        const response = await fetch(url);
    // … function body truncated (11 lines)
};

// Function with multiple overloads
function overloadedFunction(value: string): string;
function overloadedFunction(value: number): number;
function overloadedFunction(value: string | number): string | number {
    if (typeof value === 'string') {
        return value.toUpperCase();
    // … function body truncated (3 lines)
}

// Generic function
function processArray<T>(items: T[], processor: (item: T) => T): T[] {
    const result: T[] = [];
    
    for (const item of items) {
    // … function body truncated (8 lines)
    
    return result;
}

// Default export function
export default function main(): void {
    const calc = new Calculator("test");
    // … function body truncated (10 lines)
}
