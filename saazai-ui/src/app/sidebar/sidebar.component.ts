import { Component, EventEmitter, OnInit, Output, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ApiService } from '../api.service';
import { Router, NavigationEnd } from '@angular/router';

@Component({
    selector: 'app-sidebar',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './sidebar.component.html',
    styleUrl: './sidebar.component.css'
})
export class SidebarComponent implements OnInit {
    documents: string[] = [];
    selectedFile: string | null = null;

    @Output() fileSelected = new EventEmitter<string>();
    @Output() adminClicked = new EventEmitter<void>();

    constructor(private api: ApiService, private router: Router, private cdr: ChangeDetectorRef) {
        this.router.events.subscribe(val => {
            if (val instanceof NavigationEnd && val.url === '/') {
                this.refreshDocuments();
            }
        });
    }

    ngOnInit(): void {
        this.refreshDocuments();
    }

    refreshDocuments() {
        this.api.getDocuments().subscribe({
            next: (res) => {
                this.documents = res.documents;
                this.cdr.detectChanges(); // Force UI update
            },
            error: (err) => {
                console.error('API Error:', err);
            }
        });
    }

    selectFile(file: string) {
        this.selectedFile = file;
        this.fileSelected.emit(file);
    }

    onAdmin() {
        this.adminClicked.emit();
    }
}
