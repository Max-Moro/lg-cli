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
    
    constructor(name: string = "default") // … method omitted (4)
    
    public add(a: number, b: number): number // … method omitted (6)
    
    public multiply(a: number, b: number): number // … method omitted (5)
    
    public getHistory(): string[] {
        return [...this.history];
    }
    
    private validateInput(value: number): boolean // … method omitted (11)
}

export function processUserData(users: User[]): { valid: User[], invalid: User[] } // … body omitted (13)

// Arrow functions for testing different function types
const simpleArrow = () => "simple";

const complexArrow = (data: string[]) => // … body omitted (8);

const asyncArrow = async (url: string): Promise<any> => // … body omitted (15);

// Function with multiple overloads
function overloadedFunction(value: string): string;
function overloadedFunction(value: number): number;
function overloadedFunction(value: string | number): string | number // … body omitted (7)

// Generic function
function processArray<T>(items: T[], processor: (item: T) => T): T[] // … body omitted (14)

// Default export function
export default function main(): void // … body omitted (13)
