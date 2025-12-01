/**
 * TypeScript module for testing public API filtering.
 */

// … import omitted

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
// … interface omitted

// Public type alias (should be preserved)
export type UserRole = 'admin' | 'user' | 'guest';

// Public class with mixed visibility members
export class UserManager {
    // Public properties
    public readonly version: string = PUBLIC_VERSION;
    public isInitialized: boolean = false;
    
    // Private properties (should be filtered out with public_api_only)
    // … 2 fields omitted
    
    // Protected properties (should be filtered out)
    // … field omitted
    
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
    // … 4 methods omitted
    
    // Protected methods (should be filtered out)
    // … 2 methods omitted
    
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
    // … method omitted
    
    // Public readonly property with getter
    public get userCount(): number {
        return this.internalCache.size;
    }
    
    // Private readonly property with getter (should be filtered out)
    // … method omitted
    
    // Private property declaration
    // … field omitted
}

// Private class (not exported, should be filtered out)
// … class omitted

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
// … enum omitted (5 lines)

// Public functions (should be preserved)
export function createUserManager(endpoint?: string): UserManager {
    return new UserManager(endpoint);
}

export function isValidUserRole(role: any): role is UserRole {
    return UserManager.validateUserRole(role);
}

// Private functions (not exported, should be filtered out)
// … 2 functions omitted

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
    // … function omitted
}

// Private namespace (not exported, should be filtered out)
// … namespace omitted (15 lines)

// Default export (should be preserved)
export default UserManager;

// ============= Examples with TypeScript decorators =============

// Simple decorator examples
// … 2 functions omitted

// … class omitted

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
    
    // … method omitted
}

// Decorated functions
@logged
// … function omitted

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
// … interface omitted

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
    
    // … 2 methods omitted
}

// Multiple stacked decorators on private elements
// … class omitted

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
