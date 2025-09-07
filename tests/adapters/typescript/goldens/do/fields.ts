/**
 * TypeScript module for testing field optimization (constructors, getters, setters).
 */

// Simple class with trivial constructor
export class TrivialConstructorClass {
    public name: string;
    public age: number;
    public email: string;
    public createdAt: Date;
    
    constructor(name: string, age: number, email: string) {
        // Trivial constructor - only simple field assignments
        super();
        this.name = name;
        this.age = age;
        this.email = email;
        this.createdAt = new Date();
    }
}

// Class with non-trivial constructor
export class NonTrivialConstructorClass {
    public name: string;
    public age: number;
    public email: string;
    public metadata: Record<string, any>;
    
    constructor(data: any) {
        // Non-trivial constructor with validation and processing
        super();
        
        if (!data || typeof data !== 'object') {
            throw new Error('Data must be an object');
        }
        
        // Complex initialization logic
        this.name = this.validateAndFormatName(data.name);
        this.age = this.validateAge(data.age);
        this.email = this.validateEmail(data.email);
        this.metadata = this.processMetadata(data);
    }
    
    private validateAndFormatName(name: any): string {
        if (typeof name !== 'string' || !name.trim()) {
            throw new Error('Name must be a non-empty string');
        }
        return name.trim().toLowerCase();
    }
    
    private validateAge(age: any): number {
        const numAge = Number(age);
        if (isNaN(numAge) || numAge < 0 || numAge > 150) {
            throw new Error('Age must be a valid number between 0 and 150');
        }
        return numAge;
    }
    
    private validateEmail(email: any): string {
        if (typeof email !== 'string' || !email.includes('@')) {
            throw new Error('Email must be a valid email address');
        }
        return email.toLowerCase();
    }
    
    private processMetadata(data: any): Record<string, any> {
        const { name, age, email, ...rest } = data;
        return rest;
    }
}

// Class with property-based getters and setters
export class PropertyAccessorClass {
    private _value: number = 0;
    private _name: string = '';
    private _items: string[] = [];
    private _config: any = {};
    
    constructor(initialValue: number = 0) {
        this._value = initialValue;
    }
    
    // Trivial getter (should be stripped)
    get value(): number {
        return this._value;
    }
    
    // Trivial setter (should be stripped)
    set value(newValue: number) {
        this._value = newValue;
    }
    
    // Another trivial getter
    get name(): string {
        return this._name;
    }
    
    // Another trivial setter
    set name(newName: string) {
        this._name = newName;
    }
    
    // Non-trivial getter with computation
    get computedValue(): string {
        const base = `Value: ${this._value}`;
        if (this._name) {
            return `${base}, Name: ${this._name}`;
        }
        return base.toUpperCase();
    }
    
    // Trivial getter returning copy
    get items(): string[] {
        return [...this._items];
    }
    
    // Non-trivial setter with validation
    set items(newItems: string[]) {
        if (!Array.isArray(newItems)) {
            throw new TypeError('Items must be an array');
        }
        
        const validatedItems: string[] = [];
        for (const item of newItems) {
            if (typeof item === 'string' && item.trim()) {
                validatedItems.push(item.trim());
            }
        }
        
        this._items = validatedItems;
    }
    
    // Trivial getter for config
    get config(): any {
        return this._config;
    }
    
    // Trivial setter for config
    set config(newConfig: any) {
        this._config = newConfig;
    }
}

// Class with traditional get/set methods
export class TraditionalAccessorClass {
    private _data: Record<string, any> = {};
    private _count: number = 0;
    private _status: string = 'inactive';
    private _metadata: any = null;
    
    // Trivial getter methods
    getData(): Record<string, any> {
        return this._data;
    }
    
    getCount(): number {
        return this._count;
    }
    
    getStatus(): string {
        return this._status;
    }
    
    getMetadata(): any {
        return this._metadata;
    }
    
    // Trivial setter methods
    setData(data: Record<string, any>): void {
        this._data = data;
    }
    
    setCount(count: number): void {
        this._count = count;
    }
    
    setMetadata(metadata: any): void {
        this._metadata = metadata;
    }
    
    // Non-trivial setter with validation
    setStatus(status: string): void {
        const validStatuses = ['active', 'inactive', 'pending', 'error'];
        if (!validStatuses.includes(status)) {
            throw new Error(`Status must be one of: ${validStatuses.join(', ')}`);
        }
        
        this._status = status;
        this.logStatusChange(status);
    }
    
    private logStatusChange(newStatus: string): void {
        console.log(`Status changed to: ${newStatus}`);
    }
}

// Class mixing trivial and non-trivial field operations
export class MixedFieldOperationsClass {
    public name: string;
    public id: string;
    public config: any;
    public initialized: boolean;
    
    private _internalState: any = {};
    
    constructor(name: string, config?: any) {
        // Mixed constructor - some trivial, some complex
        // Trivial assignments
        this.name = name;
        this.id = '';
        
        // Non-trivial initialization
        if (!config) {
            config = this.generateDefaultConfig();
        }
        
        this.config = this.validateAndProcessConfig(config);
        this.initialized = true;
        this.id = this.generateUniqueId();
    }
    
    private generateDefaultConfig(): any {
        return {
            debug: false,
            timeout: 30000,
            retries: 3,
            logLevel: 'info'
        };
    }
    
    private validateAndProcessConfig(config: any): any {
        const requiredKeys = ['debug', 'timeout', 'retries'];
        for (const key of requiredKeys) {
            if (!(key in config)) {
                throw new Error(`Missing required config key: ${key}`);
            }
        }
        
        return { ...config, validated: true };
    }
    
    private generateUniqueId(): string {
        return `${this.name}_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    }
    
    // Trivial property getter
    get displayName(): string {
        return this.name;
    }
    
    // Non-trivial property with computation
    get fullInfo(): any {
        return {
            name: this.name,
            id: this.id,
            config: this.config,
            status: this.initialized ? 'ready' : 'pending',
            timestamp: new Date().toISOString()
        };
    }
    
    // Trivial internal state getter
    get internalState(): any {
        return this._internalState;
    }
    
    // Trivial internal state setter
    set internalState(state: any) {
        this._internalState = state;
    }
}

// Edge cases for constructor optimization

// Empty constructor
export class EmptyConstructorClass {
    constructor() {
        // Empty constructor - should be considered trivial
    }
}

// Constructor with only super() call
export class SuperOnlyConstructorClass extends EmptyConstructorClass {
    constructor() {
        // Constructor with only super() call
        super();
    }
}

// Constructor with docstring only
export class DocstringOnlyConstructorClass {
    constructor() {
        /**
         * Constructor with detailed documentation.
         * 
         * This constructor doesn't do anything except
         * provide documentation. Should be considered trivial.
         */
    }
}

// Class with readonly properties set in constructor
export class ReadonlyPropertiesClass {
    readonly id: string;
    readonly createdAt: Date;
    readonly version: number;
    
    constructor(id: string) {
        // Trivial constructor setting readonly properties
        this.id = id;
        this.createdAt = new Date();
        this.version = 1;
    }
}

// Abstract class with mixed constructor complexity
export abstract class AbstractBaseClass {
    protected name: string;
    
    constructor(name: string) {
        // Simple assignment in abstract class
        this.name = name;
    }
    
    abstract processData(): void;
    
    // Trivial getter in abstract class
    get serviceName(): string {
        return this.name;
    }
}
