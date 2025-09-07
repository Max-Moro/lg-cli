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
    
    constructor(private apiUrl: string) // … method omitted (3)
    
    getUsers(): Observable<User[]> // … method omitted (8)
    
    addUser(user: User): Promise<User> // … method omitted (7)
    
    private validateUser(user: User): boolean // … method omitted (3)
}

const createService = (url: string) => // … body omitted (3);

export { UserService, User };
