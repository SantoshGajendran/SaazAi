import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
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
export class WorkspaceComponent implements OnInit {
    documents: string[] = [];

    constructor(
        public sync: DocumentSyncService,
        private api: ApiService
    ) {}

    ngOnInit(): void {
        this.api.getDocuments().subscribe(res => {
            this.documents = res.documents;
            if (this.documents.length > 0) {
                this.sync.setActiveDocument(this.documents[0]);
            }
        });
    }

    onDocumentChange(event: Event): void {
        const select = event.target as HTMLSelectElement;
        this.sync.setActiveDocument(select.value);
    }
}
