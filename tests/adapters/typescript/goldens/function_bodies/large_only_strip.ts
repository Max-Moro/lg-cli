// TypeScript module
import { Component } from '@angular/core';
import { Observable } from 'rxjs';

interface User {
    id: number;
    name: string;
    email?: string;
}

class UserService {
    private users: User[] = [];
    
    constructor(private apiUrl: string) {
        this.apiUrl = apiUrl;
    }
    
    getUsers(): Observable<User[]> // … method omitted (8)
    
    addUser(user: User): Promise<User> // … method omitted (7)
    
    private validateUser(user: User): boolean {
        return user.name.length > 0 && user.id > 0;
    }
}

const createService = (url: string) => {
    return new UserService(url);
};

export { UserService, User };
