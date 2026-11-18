import { Routes } from '@angular/router';
import { WorkspaceComponent } from './workspace/workspace.component';
import { AdminComponent } from './admin/admin.component';

export const routes: Routes = [
    { path: '', component: WorkspaceComponent },
    { path: 'admin', component: AdminComponent },
    { path: '**', redirectTo: '' }
];
