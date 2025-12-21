
export class Calculator {
    private history: string[] = [];
    
    constructor(name: string) {
        // … method body omitted (2 lines)
    }
    
    add(a: number, b: number): number {
        // … method body omitted (3 lines)
    }
    
    getHistory(): string[] {
        return [...this.history];
    }
}
