# Dual-Pane Synchronized Interactive Workspace Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Transform SaazAi into a dual-pane engineering workspace pairing an interactive PDF canvas (with coordinate bounding-box highlights) with real-time SSE streaming intelligence.

**Architecture:** A FastAPI backend exposing HTTP Range document streaming and Server-Sent Events (SSE) inference, coupled with an Angular 17+ dual-pane frontend leveraging PDF.js, SVG vector overlays, and an RxJS synchronization hub (`DocumentSyncService`).

**Tech Stack:** FastAPI, LlamaIndex, Ollama, PyMuPDF, Angular 17+, PDF.js (`pdfjs-dist`), RxJS, ngx-markdown.

**Spec:** [`docs/superpowers/specs/2026-11-18-dual-pane-interactive-canvas-design.md`](file:///c:/Santosh/Development/Saazai(PDFLLM)/docs/superpowers/specs/2026-11-18-dual-pane-interactive-canvas-design.md)

## Global Constraints
- Target Branch: `feature/immersive-interactive-ui`
- Read/Write boundaries: All backend modifications reside within `rag_app/`. All frontend modifications reside within `saazai-ui/`.
- Strict path sanitization on all document file reads (`os.path.basename` validation).
- Zero blocking operations on the frontend UI thread; all PDF rendering must support cancellation (`renderTask.cancel()`).

---

## Tasks

### Task 1: Backend Range-Supported Raw Document Server

**Files:**
- Modify: `rag_app/api.py:100-120`
- Create: `rag_app/tests/test_raw_document.py`
- Modify: `rag_app/requirements.txt:10-15`

**Interfaces:**
- Consumes: `rag_app/data/<filename>` on disk.
- Produces: `GET /documents/{filename}/raw` returning `FileResponse` with `Accept-Ranges: bytes` support and `400` status on directory traversal attempts.

- [ ] **Step 1: Add test dependencies to `rag_app/requirements.txt`**

Append `pytest`, `pytest-asyncio`, and `httpx` to `rag_app/requirements.txt`:
```txt
pytest
pytest-asyncio
httpx
```

- [ ] **Step 2: Write failing tests for `/documents/{filename}/raw`**

Create `rag_app/tests/test_raw_document.py`:
```python
import os
import pytest
from fastapi.testclient import TestClient
import sys

# Ensure rag_app is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import app

client = TestClient(app)

def test_get_raw_document_success(tmp_path):
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    os.makedirs(data_dir, exist_ok=True)
    sample_file = os.path.join(data_dir, "test_manual.pdf")
    with open(sample_file, "wb") as f:
        f.write(b"%PDF-1.4 sample content for testing range requests")
    
    try:
        response = client.get("/documents/test_manual.pdf/raw")
        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert response.content.startswith(b"%PDF-1.4")
    finally:
        if os.path.exists(sample_file):
            os.remove(sample_file)

def test_get_raw_document_path_traversal():
    response = client.get("/documents/..%2F..%2F.env/raw")
    assert response.status_code in (400, 404)

def test_get_raw_document_not_found():
    response = client.get("/documents/non_existent_file_999.pdf/raw")
    assert response.status_code == 404
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m pytest rag_app/tests/test_raw_document.py -v`  
Expected: FAIL with `404 Not Found` (endpoint not implemented).

- [ ] **Step 4: Implement `/documents/{filename}/raw` in `rag_app/api.py`**

Add endpoint in `rag_app/api.py`:
```python
from fastapi.responses import FileResponse

@app.get("/documents/{filename}/raw")
def get_raw_document(filename: str):
    """Streams raw PDF binary file with HTTP Range support."""
    clean_name = os.path.basename(filename)
    if clean_name != filename or not clean_name:
        raise HTTPException(status_code=400, detail="Invalid filename parameter.")
        
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, "data")
    file_path = os.path.join(data_dir, clean_name)
    
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Document not found.")
        
    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=clean_name
    )
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m pytest rag_app/tests/test_raw_document.py -v`  
Expected: PASS (all 3 tests pass).

- [ ] **Step 6: Commit changes**

```bash
git add rag_app/requirements.txt rag_app/api.py rag_app/tests/test_raw_document.py
git commit -m "feat(api): add range-supported raw document endpoint"
```

---

### Task 2: Backend Real-Time SSE Inference Stream

**Files:**
- Modify: `rag_app/rag.py:100-124`
- Modify: `rag_app/api.py:165-210`
- Create: `rag_app/tests/test_chat_stream.py`

**Interfaces:**
- Consumes: `ChatRequest(query: str, selected_file: str)`.
- Produces: `POST /chat/stream` yielding `text/event-stream` with `token`, `citation`, and `done` event types.

- [ ] **Step 1: Write failing test for `POST /chat/stream`**

Create `rag_app/tests/test_chat_stream.py`:
```python
import os
import pytest
from fastapi.testclient import TestClient
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from api import app

client = TestClient(app)

def test_chat_stream_missing_body():
    response = client.post("/chat/stream", json={})
    assert response.status_code == 422

def test_chat_stream_empty_query():
    response = client.post("/chat/stream", json={"query": "", "selected_file": "manual.pdf"})
    assert response.status_code in (400, 422)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest rag_app/tests/test_chat_stream.py -v`  
Expected: FAIL with `404 Not Found` (endpoint not defined).

- [ ] **Step 3: Implement streaming generator in `rag_app/api.py`**

In `rag_app/api.py`, add `POST /chat/stream`:
```python
from fastapi.responses import StreamingResponse
import json
import asyncio

@app.post("/chat/stream")
async def chat_stream_endpoint(request: ChatRequest):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty.")
        
    chat_engine = get_chat_engine(selected_file=request.selected_file)
    if not chat_engine:
        raise HTTPException(status_code=400, detail="Chat engine not initialized.")

    async def event_generator():
        try:
            # Execute streaming chat
            response_stream = chat_engine.stream_chat(request.query)
            
            # 1. Stream tokens as they generate
            for token in response_stream.response_gen:
                payload = json.dumps({"delta": token})
                yield f"event: token\ndata: {payload}\n\n"
                await asyncio.sleep(0.01) # Yield to event loop
            
            # 2. Emit citations from source nodes
            if hasattr(response_stream, "source_nodes") and response_stream.source_nodes:
                for node in response_stream.source_nodes:
                    fn = node.metadata.get("file_name", request.selected_file)
                    pg = node.metadata.get("page_label", "1")
                    score = float(node.score) if node.score else 0.0
                    snippet = node.get_text()[:120].strip()
                    cite_payload = json.dumps({
                        "file": fn,
                        "page": int(pg) if str(pg).isdigit() else 1,
                        "anchor": snippet,
                        "score": round(score, 3)
                    })
                    yield f"event: citation\ndata: {cite_payload}\n\n"

            # 3. Emit termination event
            yield f"event: done\ndata: {{}}\n\n"

        except Exception as e:
            err_payload = json.dumps({"message": str(e)})
            yield f"event: error\ndata: {err_payload}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m pytest rag_app/tests/test_chat_stream.py -v`  
Expected: PASS.

- [ ] **Step 5: Commit changes**

```bash
git add rag_app/api.py rag_app/tests/test_chat_stream.py
git commit -m "feat(api): add SSE streaming endpoint for conversational RAG"
```

---

### Task 3: Frontend State Synchronization Hub (`DocumentSyncService`)

**Files:**
- Create: `saazai-ui/src/app/services/document-sync.service.ts`
- Create: `saazai-ui/src/app/services/document-sync.service.spec.ts`

**Interfaces:**
- Consumes: User click events and PDF selection events.
- Produces: Observables `activeDocument$`, `navigationTrigger$`, `selectionTrigger$`, `zoomLevel$`.

- [ ] **Step 1: Write unit tests for `DocumentSyncService`**

Create `saazai-ui/src/app/services/document-sync.service.spec.ts`:
```typescript
import { TestBed } from '@angular/core/testing';
import { DocumentSyncService } from './document-sync.service';

describe('DocumentSyncService', () => {
    let service: DocumentSyncService;

    beforeEach(() => {
        TestBed.configureTestingModule({});
        service = TestBed.inject(DocumentSyncService);
    });

    it('should be created', () => {
        expect(service).toBeTruthy();
    });

    it('should emit navigation payload when navigateTo is called', (done) => {
        service.navigationTrigger$.subscribe(target => {
            if (target) {
                expect(target.page).toBe(3);
                expect(target.anchorText).toBe('18V DC');
                done();
            }
        });
        service.navigateTo(3, '18V DC');
    });

    it('should update zoom level', (done) => {
        service.setZoom(1.5);
        service.zoomLevel$.subscribe(zoom => {
            expect(zoom).toBe(1.5);
            done();
        });
    });
});
```

- [ ] **Step 2: Implement `DocumentSyncService`**

Create `saazai-ui/src/app/services/document-sync.service.ts`:
```typescript
import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, Subject } from 'rxjs';

export interface NavigationTarget {
    page: number;
    anchorText?: string;
    bbox?: [number, number, number, number];
}

export interface CanvasSelection {
    text: string;
    page: number;
    clientX: number;
    clientY: number;
}

@Injectable({
    providedIn: 'root'
})
export class DocumentSyncService {
    private activeDocumentSubject = new BehaviorSubject<string | null>(null);
    public activeDocument$: Observable<string | null> = this.activeDocumentSubject.asObservable();

    private navigationSubject = new Subject<NavigationTarget | null>();
    public navigationTrigger$: Observable<NavigationTarget | null> = this.navigationSubject.asObservable();

    private selectionSubject = new Subject<CanvasSelection | null>();
    public selectionTrigger$: Observable<CanvasSelection | null> = this.selectionSubject.asObservable();

    private zoomSubject = new BehaviorSubject<number>(1.0);
    public zoomLevel$: Observable<number> = this.zoomSubject.asObservable();

    setActiveDocument(filename: string | null): void {
        this.activeDocumentSubject.next(filename);
    }

    navigateTo(page: number, anchorText?: string, bbox?: [number, number, number, number]): void {
        this.navigationSubject.next({ page, anchorText, bbox });
    }

    setSelection(selection: CanvasSelection | null): void {
        this.selectionSubject.next(selection);
    }

    setZoom(factor: number): void {
        const clamped = Math.min(Math.max(factor, 0.5), 3.0);
        this.zoomSubject.next(clamped);
    }

    zoomIn(): void {
        this.setZoom(this.zoomSubject.value + 0.15);
    }

    zoomOut(): void {
        this.setZoom(this.zoomSubject.value - 0.15);
    }
}
```

- [ ] **Step 3: Commit changes**

```bash
git add saazai-ui/src/app/services/document-sync.service.ts saazai-ui/src/app/services/document-sync.service.spec.ts
git commit -m "feat(ui): add DocumentSyncService for canvas-chat coordination"
```

---

### Task 4: Interactive Vector PDF Canvas (`PdfCanvasComponent`)

**Files:**
- Modify: `saazai-ui/package.json` (add `pdfjs-dist`)
- Create: `saazai-ui/src/app/pdf-canvas/pdf-canvas.component.ts`
- Create: `saazai-ui/src/app/pdf-canvas/pdf-canvas.component.html`
- Create: `saazai-ui/src/app/pdf-canvas/pdf-canvas.component.css`

**Interfaces:**
- Consumes: `DocumentSyncService.activeDocument$`, `navigationTrigger$`, `zoomLevel$`.
- Produces: `DocumentSyncService.setSelection(...)` on mouse text highlights; renders PDF pages and SVG glow polygon bounding boxes.

- [ ] **Step 1: Install `pdfjs-dist` in `saazai-ui`**

Run:
```bash
npm install pdfjs-dist@^4.0.379 --prefix saazai-ui
```

- [ ] **Step 2: Create `PdfCanvasComponent` implementation**

Create `saazai-ui/src/app/pdf-canvas/pdf-canvas.component.ts`:
```typescript
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
```

- [ ] **Step 3: Create `PdfCanvasComponent` HTML and CSS**

Create `saazai-ui/src/app/pdf-canvas/pdf-canvas.component.html`:
```html
<div class="pdf-canvas-wrapper">
    <!-- Top Canvas Toolbar -->
    <div class="canvas-header">
        <div class="page-indicator">
            Page {{ currentPage }} of {{ totalPages || 1 }}
        </div>
        <div class="zoom-controls">
            <button class="tool-btn" (click)="sync.zoomOut()" title="Zoom Out">−</button>
            <span class="zoom-text">{{ (zoomLevel * 100) | number:'1.0-0' }}%</span>
            <button class="tool-btn" (click)="sync.zoomIn()" title="Zoom In">+</button>
        </div>
    </div>

    <!-- Viewport Container -->
    <div class="canvas-viewport" #canvasContainer>
        <div class="loading-spinner" *ngIf="isLoading">
            <div class="ring"></div>
            <span>Loading Document Canvas...</span>
        </div>
    </div>

    <!-- Glowing Vector Overlay -->
    <svg class="svg-highlight-layer" *ngIf="currentHighlight">
        <polygon [attr.points]="currentHighlight.points" class="glow-polygon" />
    </svg>
</div>
```

Create `saazai-ui/src/app/pdf-canvas/pdf-canvas.component.css`:
```css
.pdf-canvas-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: #0d1117;
    border-right: 1px solid rgba(255, 255, 255, 0.08);
    position: relative;
    overflow: hidden;
}

.canvas-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.5rem 1rem;
    background-color: #161b22;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    color: #c9d1d9;
    font-size: 0.85rem;
    font-family: 'JetBrains Mono', monospace;
}

.zoom-controls {
    display: flex;
    align-items: center;
    gap: 0.4rem;
}

.tool-btn {
    background: #21262d;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #f0f6fc;
    width: 26px;
    height: 26px;
    border-radius: 4px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1rem;
}

.tool-btn:hover {
    background: #30363d;
}

.zoom-text {
    min-width: 45px;
    text-align: center;
}

.canvas-viewport {
    flex: 1;
    overflow: auto;
    display: flex;
    justify-content: center;
    padding: 1.5rem;
}

.canvas-viewport canvas {
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.5);
    border-radius: 4px;
    background-color: #ffffff;
}

.svg-highlight-layer {
    position: absolute;
    top: 50px;
    left: 0;
    width: 100%;
    height: calc(100% - 50px);
    pointer-events: none;
}

.glow-polygon {
    fill: rgba(239, 68, 68, 0.25);
    stroke: #ef4444;
    stroke-width: 2;
    filter: drop-shadow(0 0 8px rgba(239, 68, 68, 0.6));
    animation: pulse-glow 1.5s infinite alternate ease-in-out;
}

@keyframes pulse-glow {
    0% { opacity: 0.4; }
    100% { opacity: 1; }
}

.loading-spinner {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    color: #8b949e;
    gap: 1rem;
}
```

- [ ] **Step 4: Commit changes**

```bash
git add saazai-ui/package.json saazai-ui/src/app/pdf-canvas/
git commit -m "feat(ui): implement PdfCanvasComponent with range loading and SVG highlights"
```

---

### Task 5: Intelligence Notebook Panel with Real-Time SSE Stream

**Files:**
- Create: `saazai-ui/src/app/intelligence-panel/intelligence-panel.component.ts`
- Create: `saazai-ui/src/app/intelligence-panel/intelligence-panel.component.html`
- Create: `saazai-ui/src/app/intelligence-panel/intelligence-panel.component.css`

**Interfaces:**
- Consumes: User prompt input and `DocumentSyncService.activeDocument$`.
- Produces: Calls `POST /chat/stream` via `fetch`, renders streaming tokens, emits citation clicks to `DocumentSyncService.navigateTo(page, anchor)`.

- [ ] **Step 1: Create `IntelligencePanelComponent` TypeScript**

Create `saazai-ui/src/app/intelligence-panel/intelligence-panel.component.ts`:
```typescript
import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarkdownModule } from 'ngx-markdown';
import { DocumentSyncService } from '../services/document-sync.service';
import { Subscription } from 'rxjs';

interface Citation {
    file: string;
    page: number;
    anchor: string;
    score: number;
}

interface MessageItem {
    role: 'user' | 'assistant';
    content: string;
    citations?: Citation[];
}

@Component({
    selector: 'app-intelligence-panel',
    standalone: true,
    imports: [CommonModule, FormsModule, MarkdownModule],
    templateUrl: './intelligence-panel.component.html',
    styleUrl: './intelligence-panel.component.css'
})
export class IntelligencePanelComponent implements OnInit, OnDestroy {
    messages: MessageItem[] = [];
    userInput = '';
    isStreaming = false;
    activeFile: string | null = null;
    private abortCtrl: AbortController | null = null;
    private subs = new Subscription();

    constructor(
        public sync: DocumentSyncService,
        private cdr: ChangeDetectorRef
    ) {}

    ngOnInit(): void {
        this.subs.add(
            this.sync.activeDocument$.subscribe(doc => {
                if (doc !== this.activeFile) {
                    this.activeFile = doc;
                    this.messages = [];
                }
            })
        );
    }

    ngOnDestroy(): void {
        this.subs.unsubscribe();
        this.abortActiveStream();
    }

    abortActiveStream(): void {
        if (this.abortCtrl) {
            this.abortCtrl.abort();
            this.abortCtrl = null;
        }
        this.isStreaming = false;
    }

    async submitQuery(): Promise<void> {
        const query = this.userInput.trim();
        if (!query || !this.activeFile || this.isStreaming) return;

        this.userInput = '';
        this.messages.push({ role: 'user', content: query });

        const assistantMsg: MessageItem = { role: 'assistant', content: '', citations: [] };
        this.messages.push(assistantMsg);
        this.isStreaming = true;
        this.cdr.detectChanges();

        this.abortCtrl = new AbortController();

        try {
            const res = await fetch('http://localhost:8000/chat/stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, selected_file: this.activeFile }),
                signal: this.abortCtrl.signal
            });

            if (!res.body) throw new Error('ReadableStream not supported.');

            const reader = res.body.getReader();
            const decoder = new TextDecoder('utf-8');
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n\n');
                buffer = lines.pop() || '';

                for (const chunk of lines) {
                    if (chunk.startsWith('event: token')) {
                        const jsonStr = chunk.replace('event: token\ndata: ', '');
                        const data = JSON.parse(jsonStr);
                        assistantMsg.content += data.delta;
                        this.cdr.detectChanges();
                    } else if (chunk.startsWith('event: citation')) {
                        const jsonStr = chunk.replace('event: citation\ndata: ', '');
                        const cite = JSON.parse(jsonStr);
                        if (!assistantMsg.citations) assistantMsg.citations = [];
                        assistantMsg.citations.push(cite);
                        this.cdr.detectChanges();
                    }
                }
            }
        } catch (err: any) {
            if (err.name !== 'AbortError') {
                assistantMsg.content += `\n\n*[Connection interrupted: ${err.message}]*`;
            }
        } finally {
            this.isStreaming = false;
            this.cdr.detectChanges();
        }
    }

    onCitationClick(cite: Citation): void {
        this.sync.navigateTo(cite.page, cite.anchor);
    }
}
```

- [ ] **Step 2: Create HTML and CSS for `IntelligencePanelComponent`**

Create `saazai-ui/src/app/intelligence-panel/intelligence-panel.component.html`:
```html
<div class="intelligence-wrapper">
    <!-- Messages Scroll Area -->
    <div class="messages-container">
        <div *ngIf="messages.length === 0" class="empty-state">
            <span class="prompt-icon">⚡</span>
            <h3>Technical Notebook</h3>
            <p>Query specifications, tolerances, or diagrams from {{ activeFile || 'the active manual' }}.</p>
        </div>

        <div *ngFor="let msg of messages" class="message-block" [class.user]="msg.role === 'user'">
            <div class="meta-label">
                {{ msg.role === 'user' ? 'OPERATOR' : 'SAAZAI INTELLIGENCE' }}
            </div>
            <div class="message-body">
                <markdown [data]="msg.content"></markdown>
            </div>

            <!-- Citations Row -->
            <div class="citations-row" *ngIf="msg.citations && msg.citations.length > 0">
                <button *ngFor="let cite of msg.citations" class="citation-chip" (click)="onCitationClick(cite)">
                    📌 Page {{ cite.page }} <span class="score">({{ (cite.score * 100) | number:'1.0-0' }}%)</span>
                </button>
            </div>
        </div>
    </div>

    <!-- Input Bar -->
    <div class="input-container">
        <input 
            type="text" 
            [(ngModel)]="userInput" 
            (keyup.enter)="submitQuery()"
            placeholder="Inquire specifications, diagrams, components..." 
            [disabled]="isStreaming || !activeFile"
        />
        <button class="send-btn" (click)="submitQuery()" [disabled]="isStreaming || !userInput.trim()">
            {{ isStreaming ? '◼' : '➤' }}
        </button>
    </div>
</div>
```

Create `saazai-ui/src/app/intelligence-panel/intelligence-panel.component.css`:
```css
.intelligence-wrapper {
    display: flex;
    flex-direction: column;
    height: 100%;
    background-color: #0b0f17;
    color: #e6edf3;
    font-family: 'Plus Jakarta Sans', sans-serif;
}

.messages-container {
    flex: 1;
    overflow-y: auto;
    padding: 1.5rem;
    display: flex;
    flex-direction: column;
    gap: 1.5rem;
}

.message-block {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
    max-width: 90%;
}

.message-block.user {
    align-self: flex-end;
}

.meta-label {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.05em;
    color: #8b949e;
}

.message-body {
    background-color: #161d2a;
    border: 1px solid rgba(255, 255, 255, 0.08);
    padding: 1rem 1.25rem;
    border-radius: 8px;
    font-size: 0.92rem;
    line-height: 1.6;
}

.message-block.user .message-body {
    background-color: #1f293d;
    border-color: rgba(239, 68, 68, 0.2);
}

.citations-row {
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.4rem;
}

.citation-chip {
    background: #1c2433;
    border: 1px solid rgba(239, 68, 68, 0.3);
    color: #f87171;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    cursor: pointer;
    transition: all 0.15s ease;
}

.citation-chip:hover {
    background: rgba(239, 68, 68, 0.15);
    border-color: #ef4444;
}

.score {
    color: #8b949e;
}

.input-container {
    padding: 1rem 1.5rem;
    background-color: #121824;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    gap: 0.75rem;
}

.input-container input {
    flex: 1;
    background: #1a2233;
    border: 1px solid rgba(255, 255, 255, 0.1);
    color: #ffffff;
    padding: 0.75rem 1rem;
    border-radius: 6px;
    font-size: 0.9rem;
    outline: none;
}

.input-container input:focus {
    border-color: #ef4444;
}

.send-btn {
    background: #ef4444;
    color: white;
    border: none;
    border-radius: 6px;
    padding: 0 1.2rem;
    cursor: pointer;
    font-weight: 600;
}

.send-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
}
```

- [ ] **Step 3: Commit changes**

```bash
git add saazai-ui/src/app/intelligence-panel/
git commit -m "feat(ui): implement IntelligencePanelComponent with real-time SSE streaming"
```

---

### Task 6: Dual-Pane Workspace Container (`WorkspaceComponent`)

**Files:**
- Create: `saazai-ui/src/app/workspace/workspace.component.ts`
- Create: `saazai-ui/src/app/workspace/workspace.component.html`
- Create: `saazai-ui/src/app/workspace/workspace.component.css`
- Modify: `saazai-ui/src/app/app.routes.ts`

**Interfaces:**
- Consumes: Combines `PdfCanvasComponent` (left) and `IntelligencePanelComponent` (right) in a resizable CSS grid layout.
- Produces: Primary `/workspace` route view.

- [ ] **Step 1: Create `WorkspaceComponent`**

Create `saazai-ui/src/app/workspace/workspace.component.ts`:
```typescript
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
```

Create `saazai-ui/src/app/workspace/workspace.component.html`:
```html
<div class="workspace-layout">
    <!-- Omnipresent Top Navigation Bar -->
    <header class="workspace-header">
        <div class="brand">
            <span class="logo-dot"></span>
            <strong>SAAZAI</strong> WORKSPACE
        </div>
        <div class="doc-selector">
            <label>Manual:</label>
            <select (change)="onDocumentChange($event)">
                <option *ngFor="let doc of documents" [value]="doc">{{ doc }}</option>
            </select>
        </div>
        <div class="action-shortcuts">
            <span class="key-chip">⌘K</span>
        </div>
    </header>

    <!-- Dual Pane Split Grid -->
    <main class="split-viewport">
        <section class="left-pane">
            <app-pdf-canvas></app-pdf-canvas>
        </section>
        <section class="right-pane">
            <app-intelligence-panel></app-intelligence-panel>
        </section>
    </main>
</div>
```

Create `saazai-ui/src/app/workspace/workspace.component.css`:
```css
.workspace-layout {
    display: flex;
    flex-direction: column;
    height: 100vh;
    width: 100vw;
    overflow: hidden;
    background-color: #0d1117;
}

.workspace-header {
    height: 48px;
    background-color: #161b22;
    border-bottom: 1px solid rgba(255, 255, 255, 0.08);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1.25rem;
    color: #e6edf3;
    font-size: 0.85rem;
}

.brand {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    letter-spacing: 0.05em;
}

.logo-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background-color: #ef4444;
}

.doc-selector select {
    background: #0b0f17;
    border: 1px solid rgba(255, 255, 255, 0.15);
    color: #ffffff;
    padding: 0.25rem 0.6rem;
    border-radius: 4px;
    font-size: 0.8rem;
    margin-left: 0.5rem;
}

.key-chip {
    background: #21262d;
    padding: 0.2rem 0.4rem;
    border-radius: 4px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.75rem;
    color: #8b949e;
}

.split-viewport {
    flex: 1;
    display: grid;
    grid-template-columns: 55% 45%;
    overflow: hidden;
}

.left-pane, .right-pane {
    height: 100%;
    overflow: hidden;
}
```

- [ ] **Step 2: Connect `WorkspaceComponent` to `saazai-ui/src/app/app.routes.ts`**

Update `saazai-ui/src/app/app.routes.ts`:
```typescript
import { Routes } from '@angular/router';
import { WorkspaceComponent } from './workspace/workspace.component';
import { AdminComponent } from './admin/admin.component';

export const routes: Routes = [
    { path: '', component: WorkspaceComponent },
    { path: 'admin', component: AdminComponent },
    { path: '**', redirectTo: '' }
];
```

- [ ] **Step 3: Commit changes**

```bash
git add saazai-ui/src/app/workspace/ saazai-ui/src/app/app.routes.ts
git commit -m "feat(ui): connect dual-pane WorkspaceComponent as default application view"
```

---

### Task 7: End-to-End Build & Functional Verification

**Files:**
- Test: `rag_app/tests/test_raw_document.py`
- Test: `rag_app/tests/test_chat_stream.py`

- [ ] **Step 1: Execute backend unit test suite**

Run:
```bash
python -m pytest rag_app/tests/ -v
```
Expected: PASS (all tests green).

- [ ] **Step 2: Build Angular frontend production bundle**

Run:
```bash
npm run build --prefix saazai-ui
```
Expected: Build succeeds with zero compilation errors.

- [ ] **Step 3: Commit finalized verification state**

```bash
git add .
git commit -m "chore: verify backend unit tests and frontend production build"
git push origin feature/immersive-interactive-ui
```
