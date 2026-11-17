import { Component, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../api.service';
import { Router } from '@angular/router';
import { SuccessModalComponent } from '../success-modal/success-modal';
import { DeleteModalComponent } from '../delete-modal/delete-modal.component';

@Component({
    selector: 'app-admin',
    standalone: true,
    imports: [CommonModule, FormsModule, SuccessModalComponent, DeleteModalComponent],
    templateUrl: './admin.component.html',
    styleUrl: './admin.component.css'
})
export class AdminComponent implements OnInit {
    isAuthenticated = false;
    email = '';
    password = '';
    documents: string[] = [];
    storageStats = { count: 0, total_size: '0 B' };
    isUploading = false;
    uploadProgress = 0;

    showSuccessModal = false; // Add this flag

    constructor(private api: ApiService, private router: Router, private cdr: ChangeDetectorRef) { }

    ngOnInit(): void {
        // Check if previously auth (simple session check, ideally use proper auth service)
        if (sessionStorage.getItem('isAdmin') === 'true') {
            this.isAuthenticated = true;
            this.loadDocs();
        }
    }

    login() {
        // Hardcoded for demo/matching python env
        if (this.password === 'admin123') {
            this.isAuthenticated = true;
            sessionStorage.setItem('isAdmin', 'true');
            this.loadDocs();
        } else {
            alert('Invalid Password');
        }
    }

    logout() {
        this.isAuthenticated = false;
        sessionStorage.removeItem('isAdmin');
        this.email = '';
        this.password = '';
    }

    loadDocs() {
        this.api.getDocuments().subscribe({
            next: (res) => {
                this.documents = res.documents;
                this.cdr.detectChanges(); // Force UI Update
            },
            error: (err) => {
                console.error("Admin Load Docs Error: ", err);
            }
        });

        this.api.getStats().subscribe({
            next: (res) => {
                this.storageStats = res;
                this.cdr.detectChanges();
            }
        });
    }

    onFileSelected(event: any) {
        const file = event.target.files[0];
        if (file) {
            this.upload(file);
        }
    }

    upload(file: File) {
        this.isUploading = true;
        this.uploadProgress = 0;
        this.uploadStatusMessage = 'Starting upload...';

        this.api.uploadDocument(file).subscribe({
            next: (res) => {
                // Upload started successfully, now poll for status
                this.pollStatus(res.filename);
            },
            error: (err) => {
                this.isUploading = false;
                alert('Upload Failed: ' + err.message);
                this.cdr.detectChanges();
            }
        });
    }

    uploadStatusMessage = '';

    pollStatus(filename: string) {
        const intervalId = setInterval(() => {
            this.api.getUploadStatus(filename).subscribe({
                next: (res) => {
                    this.uploadStatusMessage = res.status;

                    // Map status to progress for visual bar
                    if (res.status.includes('Initializing LlamaParse')) this.uploadProgress = 10;
                    else if (res.status.includes('Parsing Document')) this.uploadProgress = 35;
                    else if (res.status.includes('Assigning metadata')) this.uploadProgress = 55;
                    else if (res.status.includes('Initializing Vector Database')) this.uploadProgress = 70;
                    else if (res.status.includes('Generating Embeddings')) this.uploadProgress = 85;
                    else if (res.status === 'Completed') this.uploadProgress = 100;

                    this.cdr.detectChanges();

                    if (res.status === 'Completed') {
                        clearInterval(intervalId);
                        setTimeout(() => {
                            this.isUploading = false;
                            this.loadDocs();
                            this.showSuccessModal = true;
                            this.uploadProgress = 0;
                            this.cdr.detectChanges();
                        }, 800);
                    } else if (res.status.startsWith('Error')) {
                        clearInterval(intervalId);
                        this.isUploading = false;
                        alert(res.status);
                        this.cdr.detectChanges();
                    }
                },
                error: () => {
                    //If poll fails, keep trying or fail silently 
                }
            });
        }, 800);
    }

    fileToDelete: string | null = null;
    showDeleteModal = false;

    delete(doc: string) {
        this.fileToDelete = doc;
        this.showDeleteModal = true;
    }

    confirmDelete() {
        if (this.fileToDelete) {
            this.api.deleteDocument(this.fileToDelete).subscribe(() => {
                this.loadDocs();
                this.cancelDelete();
                this.cdr.detectChanges(); // Force UI Update
            });
        }
    }

    cancelDelete() {
        this.showDeleteModal = false;
        this.fileToDelete = null;
    }

    backToChat() {
        this.router.navigate(['/']);
    }
}
