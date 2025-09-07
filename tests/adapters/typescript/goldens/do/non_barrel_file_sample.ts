// Regular TypeScript module
import { Component } from '@angular/core';
import { Observable } from 'rxjs';

@Component({
    selector: 'app-user',
    template: '<div>User Component</div>'
})
export class UserComponent {
    
    constructor(private userService: UserService) {}
    
    loadUsers(): Observable<User[]> {
        return this.userService.getUsers();
    }
    
    private validateUser(user: User): boolean {
        return user.name.length > 0;
    }
}

export default UserComponent;
