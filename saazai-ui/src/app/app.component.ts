import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterOutlet, Router, NavigationEnd } from '@angular/router';
import { SidebarComponent } from './sidebar/sidebar.component';

@Component({
    selector: 'app-root',
    standalone: true,
    imports: [CommonModule, RouterOutlet, SidebarComponent],
    templateUrl: './app.component.html',
    styleUrl: './app.component.css'
})
export class AppComponent {
    title = 'SzAi';
    currentRoute = '';

    constructor(private router: Router) {
        this.router.events.subscribe(event => {
            if (event instanceof NavigationEnd) {
                this.currentRoute = event.url;
            }
        });
    }

    isAdminRoute(): boolean {
        return this.currentRoute.includes('/admin');
    }

    onFileSelected(file: string) {
        // Navigate to chat with query param
        this.router.navigate(['/'], { queryParams: { file: file } });
    }

    onAdminClick() {
        this.router.navigate(['/admin']);
    }
}
