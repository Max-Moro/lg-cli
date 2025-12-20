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
    public add(a: number, b: number): number // … method body omitted (4 lines)
    
    public multiply(a: number, b: number): number {
        const result = a * b;
    public multiply(a: number, b: number): number // … method body omitted (3 lines)
    
    public getHistory(): string[] {
        return [...this.history];
    }
    
    private validateInput(value: number): boolean {
        if (typeof value !== 'number') {
    private validateInput(value: number): boolean // … method body omitted (9 lines)
}

export function processUserData(users: User[]): { valid: User[], invalid: User[] } {
    const result = { valid: [], invalid: [] };
    
export function processUserData(users: User[]): { valid: User[], invalid: User[] } // … function body omitted (10 lines)

// Arrow functions for testing different function types
const simpleArrow = () => "simple";

const complexArrow = (data: string[]) => {
    const processed = data
        .filter(item => item.length > 0)
const complexArrow = (data: string[]) => // … function body omitted (5 lines);

const asyncArrow = async (url: string): Promise<any> => {
    try {
        const response = await fetch(url);
const asyncArrow = async (url: string): Promise<any> => // … function body omitted (12 lines);

// Function with multiple overloads
function overloadedFunction(value: string): string;
function overloadedFunction(value: number): number;
function overloadedFunction(value: string | number): string | number {
    if (typeof value === 'string') {
        return value.toUpperCase();
function overloadedFunction(value: string | number): string | number // … function body omitted (4 lines)

// Generic function
function processArray<T>(items: T[], processor: (item: T) => T): T[] {
    const result: T[] = [];
    
    for (const item of items) {
function processArray<T>(items: T[], processor: (item: T) => T): T[] // … function body omitted (10 lines)

// Default export function
export default function main(): void {
    const calc = new Calculator("test");
export default function main(): void // … function body omitted (11 lines)
