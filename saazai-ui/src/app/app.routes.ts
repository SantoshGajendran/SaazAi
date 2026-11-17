import { Routes } from '@angular/router';
import { ChatComponent } from './chat/chat.component';
import { AdminComponent } from './admin/admin.component';

export const routes: Routes = [
    { path: '', component: ChatComponent },
    { path: 'admin', component: AdminComponent }
];
