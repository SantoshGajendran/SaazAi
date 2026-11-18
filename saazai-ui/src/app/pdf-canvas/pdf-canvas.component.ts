import { Component, ElementRef, OnInit, OnDestroy, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentSyncService, NavigationTarget } from '../services/document-sync.service';
import { Subscription } from 'rxjs';
import * as pdfjsLib from 'pdfjs-dist';

// Configure worker
pdfjsLib.GlobalWorkerOptions.workerSrc = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/4.0.379/pdf.worker.min.mjs';

interface HighlightPolygon {
    page: number;
    points: string;
}

@Component({
    selector: 'app-pdf-canvas',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './pdf-canvas.component.html',
    styleUrl: './pdf-canvas.component.css'
})
export class PdfCanvasComponent implements OnInit, OnDestroy {
    @ViewChild('canvasContainer') canvasContainer!: ElementRef<HTMLDivElement>;

    private subs = new Subscription();
    pdfDoc: pdfjsLib.PDFDocumentProxy | null = null;
    totalPages = 0;
    currentPage = 1;
    zoomLevel = 1.0;
    isLoading = false;
    currentHighlight: HighlightPolygon | null = null;

    constructor(
        public sync: DocumentSyncService,
        private cdr: ChangeDetectorRef
    ) {}

    ngOnInit(): void {
        this.subs.add(
            this.sync.activeDocument$.subscribe(doc => {
                if (doc) this.loadDocument(doc);
            })
        );

        this.subs.add(
            this.sync.navigationTrigger$.subscribe(target => {
                if (target) this.handleNavigation(target);
            })
        );

        this.subs.add(
            this.sync.zoomLevel$.subscribe(zoom => {
                this.zoomLevel = zoom;
                if (this.pdfDoc) this.renderPage(this.currentPage);
            })
        );
    }

    ngOnDestroy(): void {
        this.subs.unsubscribe();
    }

    async loadDocument(filename: string): Promise<void> {
        this.isLoading = true;
        this.cdr.detectChanges();
        try {
            const url = `http://localhost:8000/documents/${encodeURIComponent(filename)}/raw`;
            const loadingTask = pdfjsLib.getDocument({ url, rangeChunkSize: 65536 });
            this.pdfDoc = await loadingTask.promise;
            this.totalPages = this.pdfDoc.numPages;
            this.currentPage = 1;
            await this.renderPage(1);
        } catch (err) {
            console.error('Failed to load PDF:', err);
        } finally {
            this.isLoading = false;
            this.cdr.detectChanges();
        }
    }

    async renderPage(pageNum: number): Promise<void> {
        if (!this.pdfDoc || !this.canvasContainer) return;
        const page = await this.pdfDoc.getPage(pageNum);
        const viewport = page.getViewport({ scale: this.zoomLevel * 1.5 });

        const canvas = document.createElement('canvas');
        canvas.className = 'pdf-page-canvas';
        const ctx = canvas.getContext('2d')!;
        canvas.height = viewport.height;
        canvas.width = viewport.width;

        const container = this.canvasContainer.nativeElement;
        container.innerHTML = ''; // Clear prior render
        container.appendChild(canvas);

        await page.render({ canvasContext: ctx, viewport }).promise;
        this.currentPage = pageNum;
        this.cdr.detectChanges();
    }

    handleNavigation(target: NavigationTarget): void {
        if (target.page >= 1 && target.page <= this.totalPages) {
            this.renderPage(target.page).then(() => {
                // Draw pulsating highlight indicator
                this.currentHighlight = {
                    page: target.page,
                    points: "50,50 300,50 300,100 50,100"
                };
                this.cdr.detectChanges();
                setTimeout(() => {
                    this.currentHighlight = null;
                    this.cdr.detectChanges();
                }, 3000);
            });
        }
    }
}
