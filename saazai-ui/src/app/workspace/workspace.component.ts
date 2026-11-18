import { Component, OnInit, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ActivatedRoute } from '@angular/router';
import { Subscription } from 'rxjs';
import { PdfCanvasComponent } from '../pdf-canvas/pdf-canvas.component';
import { IntelligencePanelComponent } from '../intelligence-panel/intelligence-panel.component';
import { DocumentSyncService } from '../services/document-sync.service';
import { ApiService } from '../api.service';

@Component({
    selector: 'app-workspace',
    standalone: true,
    imports: [CommonModule, PdfCanvasComponent, IntelligencePanelComponent],
    templateUrl: './workspace.component.html',
    styleUrl: './workspace.component.css'
})
export class WorkspaceComponent implements OnInit, OnDestroy {
    documents: string[] = [];
    private subs = new Subscription();

    constructor(
        public sync: DocumentSyncService,
        private api: ApiService,
        private route: ActivatedRoute
    ) {}

    ngOnInit(): void {
        this.subs.add(
            this.route.queryParams.subscribe(params => {
                const file = params['file'];
                if (file) {
                    this.sync.setActiveDocument(file);
                }
            })
        );

        this.api.getDocuments().subscribe({
            next: (res) => {
                this.documents = res.documents || [];
                const currentDoc = this.route.snapshot.queryParams['file'];
                if (!currentDoc && this.documents.length > 0) {
                    this.sync.setActiveDocument(this.documents[0]);
                }
            },
            error: (err) => {
                console.error('Failed to load documents:', err);
            }
        });
    }

    ngOnDestroy(): void {
        this.subs.unsubscribe();
    }

    onDocumentChange(event: Event): void {
        const select = event.target as HTMLSelectElement;
        this.sync.setActiveDocument(select.value);
    }
}
