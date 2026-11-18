import { Component, ElementRef, OnInit, OnDestroy, ViewChild, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { DocumentSyncService, NavigationTarget } from '../services/document-sync.service';
import { ApiService } from '../api.service';
import { Subscription } from 'rxjs';
import * as pdfjsLib from 'pdfjs-dist';

// Configure worker dynamically matching installed version
pdfjsLib.GlobalWorkerOptions.workerSrc = `https://cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjsLib.version}/pdf.worker.min.mjs`;

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
    @ViewChild('pdfCanvas') pdfCanvas?: ElementRef<HTMLCanvasElement>;
    @ViewChild('textLayer') textLayerRef?: ElementRef<HTMLDivElement>;

    private subs = new Subscription();
    private currentRenderTask: any = null;
    private activeLoadingTask: any = null;

    pdfDoc: pdfjsLib.PDFDocumentProxy | null = null;
    totalPages = 0;
    currentPage = 1;
    zoomLevel = 1.0;
    isLoading = false;
    viewportWidth = 0;
    viewportHeight = 0;
    currentHighlight: HighlightPolygon | null = null;

    constructor(
        public sync: DocumentSyncService,
        private api: ApiService,
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
        this.cancelActiveLoadingTask();
        this.cancelActiveRender();
        if (this.pdfDoc) {
            try {
                this.pdfDoc.destroy();
            } catch {
                // ignore cleanup errors
            }
            this.pdfDoc = null;
        }
    }

    private cancelActiveLoadingTask(): void {
        if (this.activeLoadingTask) {
            try {
                this.activeLoadingTask.destroy();
            } catch {
                // ignore loading task cancellation error
            }
            this.activeLoadingTask = null;
        }
    }

    private cancelActiveRender(): void {
        if (this.currentRenderTask) {
            try {
                this.currentRenderTask.cancel();
            } catch {
                // ignore cancellation errors
            }
            this.currentRenderTask = null;
        }
    }

    async loadDocument(filename: string): Promise<void> {
        this.isLoading = true;
        this.currentHighlight = null;
        this.cdr.detectChanges();

        this.cancelActiveLoadingTask();
        this.cancelActiveRender();

        if (this.pdfDoc) {
            try {
                await this.pdfDoc.destroy();
            } catch (err) {
                console.warn('Failed to destroy previous PDF document:', err);
            }
            this.pdfDoc = null;
        }

        try {
            const url = `${this.api.apiUrl}/documents/${encodeURIComponent(filename)}/raw`;
            const loadingTask = pdfjsLib.getDocument({ url, rangeChunkSize: 65536 });
            this.activeLoadingTask = loadingTask;
            this.pdfDoc = await loadingTask.promise;
            this.activeLoadingTask = null;
            this.totalPages = this.pdfDoc.numPages;
            this.currentPage = 1;
            this.isLoading = false;
            this.cdr.detectChanges();
            await this.renderPage(1);
        } catch (err) {
            this.activeLoadingTask = null;
            console.error('Failed to load PDF:', err);
            this.isLoading = false;
            this.cdr.detectChanges();
        }
    }

    prevPage(): void {
        if (this.currentPage > 1) {
            this.renderPage(this.currentPage - 1);
        }
    }

    nextPage(): void {
        if (this.currentPage < this.totalPages) {
            this.renderPage(this.currentPage + 1);
        }
    }

    async renderPage(pageNum: number): Promise<void> {
        if (!this.pdfDoc) return;

        this.cancelActiveRender();

        try {
            const page = await this.pdfDoc.getPage(pageNum);
            const scale = this.zoomLevel * 1.5;
            const viewport = page.getViewport({ scale });

            this.viewportWidth = viewport.width;
            this.viewportHeight = viewport.height;
            this.cdr.detectChanges();

            if (!this.pdfCanvas) return;
            const canvas = this.pdfCanvas.nativeElement;
            const ctx = canvas.getContext('2d')!;
            canvas.height = viewport.height;
            canvas.width = viewport.width;

            const renderTask = page.render({ canvasContext: ctx, viewport });
            this.currentRenderTask = renderTask;

            await renderTask.promise;
            this.currentPage = pageNum;

            if (this.textLayerRef?.nativeElement) {
                const textLayerDiv = this.textLayerRef.nativeElement;
                textLayerDiv.innerHTML = '';
                textLayerDiv.style.width = `${viewport.width}px`;
                textLayerDiv.style.height = `${viewport.height}px`;

                try {
                    const textContent = await page.getTextContent();
                    const pdfAny = pdfjsLib as any;
                    if (typeof pdfAny['renderTextLayer'] === 'function') {
                        await pdfAny['renderTextLayer']({
                            textContentSource: textContent,
                            container: textLayerDiv,
                            viewport: viewport
                        }).promise;
                    } else if (pdfAny['TextLayer']) {
                        const textLayer = new pdfAny['TextLayer']({
                            textContentSource: textContent,
                            container: textLayerDiv,
                            viewport: viewport
                        });
                        await textLayer.render();
                    }
                } catch (textErr: any) {
                    console.warn('Failed to render text layer:', textErr);
                }
            }

            this.cdr.detectChanges();
        } catch (err: any) {
            if (err?.name === 'RenderingCancelledException' || err?.message?.includes('cancelled')) {
                // Render was cancelled gracefully
                return;
            }
            console.error('Failed to render page:', err);
        } finally {
            this.currentRenderTask = null;
        }
    }

    handleNavigation(target: NavigationTarget): void {
        if (target.page >= 1 && target.page <= this.totalPages) {
            this.renderPage(target.page).then(() => {
                let points: string;
                if (target.bbox && target.bbox.length === 4) {
                    const [x1, y1, x2, y2] = target.bbox;
                    const scale = this.zoomLevel * 1.5;
                    const isNormalized = x1 <= 1 && y1 <= 1 && x2 <= 1 && y2 <= 1;
                    const sx1 = Math.round(isNormalized ? x1 * this.viewportWidth : x1 * scale);
                    const sy1 = Math.round(isNormalized ? y1 * this.viewportHeight : y1 * scale);
                    const sx2 = Math.round(isNormalized ? x2 * this.viewportWidth : x2 * scale);
                    const sy2 = Math.round(isNormalized ? y2 * this.viewportHeight : y2 * scale);
                    points = `${sx1},${sy1} ${sx2},${sy1} ${sx2},${sy2} ${sx1},${sy2}`;
                } else {
                    const w = this.viewportWidth || 300;
                    const h = this.viewportHeight || 400;
                    const x1 = Math.round(w * 0.1);
                    const y1 = Math.round(h * 0.1);
                    const x2 = Math.round(w * 0.9);
                    const y2 = Math.round(h * 0.2);
                    points = `${x1},${y1} ${x2},${y1} ${x2},${y2} ${x1},${y2}`;
                }

                this.currentHighlight = {
                    page: target.page,
                    points
                };
                this.cdr.detectChanges();
                setTimeout(() => {
                    this.currentHighlight = null;
                    this.cdr.detectChanges();
                }, 3000);
            });
        }
    }

    onCanvasMouseUp(event: MouseEvent): void {
        const selection = window.getSelection();
        const text = selection ? selection.toString().trim() : '';
        if (text) {
            this.sync.setSelection({
                text,
                page: this.currentPage,
                clientX: event.clientX,
                clientY: event.clientY
            });
        }
    }
}
