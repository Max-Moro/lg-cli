/**
 * TypeScript module for testing public API filtering.
 */

import { EventEmitter } from 'events';

// Public module-level constants (should be preserved)
export const PUBLIC_VERSION = '1.0.0';
export const API_ENDPOINT = 'https://api.example.com';

// Private module-level constants (should be filtered out)
const PRIVATE_SECRET = 'internal-use-only';
const INTERNAL_CONFIG = { debug: true, verbose: false };

// Public interface (should be preserved)
export interface User {
    id: number;
    name: string;
    email: string;
    createdAt: Date;
}

// Private interface (not exported, should be filtered out)
interface InternalMetrics {
    processTime: number;
    memoryUsage: number;
}

// Public type alias (should be preserved)
export type UserRole = 'admin' | 'user' | 'guest';

// Public class with mixed visibility members
export class UserManager {
    // Public properties
    public readonly version: string = PUBLIC_VERSION;
    public isInitialized: boolean = false;
    
    // Private properties (should be filtered out with public_api_only)
    private internalCache: Map<string, User> = new Map();
    private metrics: InternalMetrics = { processTime: 0, memoryUsage: 0 };
    
    // Protected properties (should be filtered out)
    protected config: any = {};
    
    constructor(apiEndpoint: string = API_ENDPOINT) {
        this.apiEndpoint = apiEndpoint;
        this.initialize();
    }
    
    // Public methods (should be preserved)
    public async createUser(userData: Partial<User>): Promise<User> {
        this.validateUserData(userData);
        
        const user: User = {
            id: this.generateId(),
            name: userData.name!,
            email: userData.email!,
            createdAt: new Date()
        };
        
        this.internalCache.set(user.email, user);
        return user;
    }
    
    public async getUserById(id: number): Promise<User | null> {
        for (const user of this.internalCache.values()) {
            if (user.id === id) {
                return user;
            }
        }
        
        return await this.fetchUserFromApi(id);
    }
    
    public getAllUsers(): User[] {
        return Array.from(this.internalCache.values());
    }
    
    // Private methods (should be filtered out)
    private validateUserData(userData: Partial<User>): void {
        if (!userData.name || !userData.email) {
            throw new Error('Name and email are required');
        }
        
        if (!this.isValidEmail(userData.email)) {
            throw new Error('Invalid email format');
        }
    }
    
    private generateId(): number {
        return Math.floor(Math.random() * 1000000);
    }
    
    private isValidEmail(email: string): boolean {
        const emailRegex = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
        return emailRegex.test(email);
    }
    
    private async fetchUserFromApi(id: number): Promise<User | null> {
        try {
            const response = await fetch(`${this.apiEndpoint}/users/${id}`);
            if (response.ok) {
                return await response.json();
            }
        } catch (error) {
            this.logError('Failed to fetch user', error);
        }
        
        return null;
    }
    
    // Protected methods (should be filtered out)
    protected initialize(): void {
        this.config = { ...INTERNAL_CONFIG };
        this.isInitialized = true;
    }
    
    protected logError(message: string, error: any): void {
        console.error(`[UserManager] ${message}:`, error);
    }
    
    // Public static methods (should be preserved)
    public static validateUserRole(role: string): role is UserRole {
        return ['admin', 'user', 'guest'].includes(role);
    }
    
    public static createDefaultUser(): User {
        return {
            id: 0,
            name: 'Default User',
            email: 'default@example.com',
            createdAt: new Date()
        };
    }
    
    // Private static methods (should be filtered out)
    private static formatInternalId(id: number): string {
        return `internal_${id.toString().padStart(6, '0')}`;
    }
    
    // Public readonly property with getter
    public get userCount(): number {
        return this.internalCache.size;
    }
    
    // Private readonly property with getter (should be filtered out)
    private get internalState(): any {
        return {
            cacheSize: this.internalCache.size,
            metrics: this.metrics
        };
    }
    
    // Private property declaration
    private readonly apiEndpoint: string;
}

// Private class (not exported, should be filtered out)
class InternalLogger {
    private logs: string[] = [];
    
    public log(message: string): void {
        this.logs.push(`${new Date().toISOString()}: ${message}`);
    }
    
    public getLogs(): string[] {
        return [...this.logs];
    }
    
    private clearLogs(): void {
        this.logs = [];
    }
}

// Public abstract class (should be preserved)
export abstract class BaseService {
    protected abstract serviceName: string;
    
    public abstract initialize(): Promise<void>;
    
    public getServiceInfo(): { name: string; version: string } {
        return {
            name: this.serviceName,
            version: PUBLIC_VERSION
        };
    }
    
    // Protected abstract method (should be filtered out in public API)
    protected abstract validateConfig(config: any): boolean;
}

// Public enum (should be preserved)
export enum UserStatus {
    ACTIVE = 'active',
    INACTIVE = 'inactive',
    PENDING = 'pending',
    BANNED = 'banned'
}

// Private enum (not exported, should be filtered out)
enum InternalEventType {
    USER_CREATED = 'user_created',
    USER_UPDATED = 'user_updated',
    CACHE_CLEARED = 'cache_cleared'
}

// Public functions (should be preserved)
export function createUserManager(endpoint?: string): UserManager {
    return new UserManager(endpoint);
}

export function isValidUserRole(role: any): role is UserRole {
    return UserManager.validateUserRole(role);
}

// Private functions (not exported, should be filtered out)
function logInternalEvent(event: InternalEventType, data?: any): void {
    console.log(`[Internal] ${event}:`, data);
}

function processInternalMetrics(metrics: InternalMetrics): void {
    // Process internal metrics
    console.log('Processing metrics:', metrics);
}

// Exported namespace (should be preserved)
export namespace UserUtils {
    export function formatUserName(user: User): string {
        return `${user.name} (${user.email})`;
    }
    
    export function getUserAge(user: User): number {
        const now = new Date();
        const created = new Date(user.createdAt);
        return Math.floor((now.getTime() - created.getTime()) / (1000 * 60 * 60 * 24));
    }
    
    // Private namespace member (should be filtered out)
    function internalFormatting(text: string): string {
        return text.toLowerCase().replace(/\s+/g, '_');
    }
}

// Private namespace (not exported, should be filtered out)
namespace InternalUtils {
    export function debugLog(message: string): void {
        if (INTERNAL_CONFIG.debug) {
            console.log(`[Debug] ${message}`);
        }
    }
    
    export function measurePerformance<T>(fn: () => T): T {
        const start = performance.now();
        const result = fn();
        const end = performance.now();
        console.log(`Performance: ${end - start}ms`);
        return result;
    }
}

// Default export (should be preserved)
export default UserManager;

// ============= Examples with TypeScript decorators =============

// Simple decorator examples
function logged(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    const originalMethod = descriptor.value;
    descriptor.value = function (...args: any[]) {
        console.log(`Calling ${propertyKey}`);
        return originalMethod.apply(this, args);
    };
}

function validate(target: any, propertyKey: string, descriptor: PropertyDescriptor) {
    // Validation decorator
}

@logged
class PrivateDecoratedClass {
    /**
     * Private class with decorator - should be removed completely including @logged.
     */
    
    private data: string = 'private';
    
    @validate
    private processData(): string {
        return this.data.toUpperCase();
    }
}

@logged
@validate
export class PublicDecoratedClass {
    /**
     * Public class with multiple decorators - should be preserved with decorators.
     */
    
    public data: string = 'public';
    
    @logged
    public processData(): string {
        return this.data.toUpperCase();
    }
    
    @validate
    private _internalProcess(): void {
        // Private method with decorator - should remove method and decorator
    }
}

// Decorated functions
@logged
function privateDecoratedFunction(data: string): string {
    /**
     * Private function with decorator - should remove function and @logged decorator.
     */
    return data.toLowerCase();
}

@logged
@validate
export function publicDecoratedFunction(data: string): string {
    /**
     * Public function with decorators - should preserve function and decorators.
     */
    return data.toUpperCase();
}

// Interface with decorators (if supported)
@logged
interface PrivateDecoratedInterface {
    /**
     * Private interface with decorator - should remove interface and decorator.
     */
    prop: string;
}

@validate
export interface PublicDecoratedInterface {
    /**
     * Public interface with decorator - should preserve interface and decorator.
     */
    value: number;
}

// Class with mixed decorated members
export class MixedDecoratedClass {
    @logged
    public publicDecoratedMethod(): void {
        // Public method with decorator - should preserve both
    }
    
    @logged
    @validate
    private _privateDecoratedMethod(): void {
        // Private method with decorators - should remove method and both decorators
    }
    
    @validate
    protected protectedDecoratedMethod(): void {
        // Protected method with decorator - should remove method and decorator
    }
}

// Multiple stacked decorators on private elements
@logged
@validate
class PrivateMultiDecoratedClass {
    /**
     * Private class with multiple decorators - should remove class and all decorators.
     */
    
    @logged
    @validate
    private multiDecoratedMethod(): void {
        // Multiple decorators on private method
    }
}

@logged
@validate
export class PublicMultiDecoratedClass {
    /**
     * Public class with multiple decorators - should preserve class and all decorators.
     */
    
    @logged
    @validate
    public multiDecoratedMethod(): void {
        // Multiple decorators on public method - should preserve all
    }
}
