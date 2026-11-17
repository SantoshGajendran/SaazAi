# Design Spec: Dual-Pane Synchronized Interactive Workspace

**Date**: 2026-11-18  
**Branch**: `feature/immersive-interactive-ui`  
**Status**: Approved (Pending Implementation Plan)  

---

## 1. Executive Summary & Objective

Transform SaazAi from a standard conversational chatbot into a high-agency, tactile engineering workspace for technical PDF documents, schematics, and manuals. The application eliminates the generic "AI-generated" aesthetic (monolithic bubbles, generic avatars, static image dumps) in favor of a dual-pane spatial canvas combining an interactive PDF viewer on the left with a real-time streamed intelligence pane on the right. Citations actively trigger smooth coordinate navigation and ambient vector highlights in the document viewer, and document text selection triggers contextual micro-actions.

---

## 2. Architecture & System Topology

```mermaid
flowchart LR
    subgraph Backend [FastAPI / rag_app]
        STREAM["POST /chat/stream (SSE)"]
        RAW["GET /documents/{filename}/raw"]
        ENGINE["LlamaIndex Streaming Engine"]
    end

    subgraph Frontend [Angular 17+ / saazai-ui]
        SYNC["DocumentSyncService (RxJS State Hub)"]
        PDF["PdfCanvasComponent (PDF.js + SVG Overlay)"]
        PANEL["IntelligencePanelComponent (SSE Stream)"]
        CMD["CommandPaletteComponent (⌘K Selector)"]
    end

    RAW -->|Byte Range Stream| PDF
    PANEL -->|Submit Prompt| STREAM
    STREAM --> ENGINE
    ENGINE -->|Token Deltas & Nodes| STREAM
    STREAM -->|SSE 'token'| PANEL
    STREAM -->|SSE 'citation' {page, anchor, score}| PANEL
    PANEL -->|Highlight Click| SYNC
    SYNC -->|Glide & BBox Glow| PDF
    PDF -->|Text Selection| SYNC
    SYNC -->|Context Action Pill| PANEL
    CMD -->|Select Doc/Page| SYNC
```

---

## 3. Detailed Component Specifications

### 3.1 Backend Service Layer (`rag_app`)

#### 1. Range-Supported Document Server (`api.py`)
- **Route**: `GET /documents/{filename}/raw`
- **Behavior**: Streams raw binary file using FastAPI `FileResponse` or custom streaming chunk reader. Supports HTTP Range requests (`Accept-Ranges: bytes`, `206 Partial Content`).
- **Security**: Validates `filename` via `os.path.basename` and ensures canonical path stays inside `rag_app/data/` to block directory traversal.

#### 2. Streaming Inference Endpoint (`api.py` & `rag.py`)
- **Route**: `POST /chat/stream`
- **Request Body**:
  ```json
  {
    "query": "string",
    "selected_file": "string"
  }
  ```
- **Response**: `text/event-stream` emitting structured events:
  - `event: token\ndata: {"delta": "string"}\n\n`
  - `event: citation\ndata: {"file": "string", "page": 4, "anchor": "18V - 36V DC", "score": 0.91}\n\n`
  - `event: done\ndata: {}\n\n`
  - `event: error\ndata: {"message": "string"}\n\n`
- **Engine Adaptation (`rag.py`)**: Wrap `chat_engine.stream_chat(query)` to yield tokens asynchronously without thread blocking.

---

### 3.2 Frontend Architecture (`saazai-ui`)

#### 1. State Synchronization (`document-sync.service.ts`)
- **Observables**:
  - `activeDocument$: Observable<string | null>` — Currently active document filename.
  - `navigationTrigger$: Observable<{ page: number; anchorText?: string }>` — Citation navigation requests.
  - `selectionTrigger$: Observable<{ text: string; page: number; rect: DOMRect } | null>` — Text selected on PDF canvas.
  - `zoomLevel$: BehaviorSubject<number>` — Current zoom factor (0.5 to 3.0, default 1.0).

#### 2. Vector Canvas Component (`pdf-canvas.component.ts` & `.html`)
- **Dependencies**: `pdfjs-dist` (version 4.x+ with worker configured).
- **DOM Structure**:
  ```html
  <div class="canvas-viewport" (scroll)="onViewportScroll()">
    <div *ngFor="let page of visiblePages" class="page-container" [style.height.px]="page.height">
      <canvas #pageCanvas class="pdf-page"></canvas>
      <div class="text-layer" (mouseup)="onTextSelection($event, page.number)"></div>
      <svg class="annotation-overlay" [attr.viewBox]="page.viewBox">
        <!-- SVG Bounding Box Glow Highlight rendered dynamically -->
        <polygon *ngIf="page.activeHighlight" [attr.points]="page.activeHighlight.points" class="glow-polygon" />
      </svg>
    </div>
  </div>
  ```
- **Lifecycle & Cancellation**: On scroll or rapid zoom changes, active `PDFPageProxy.render()` tasks receive `.cancel()` before starting next render frame. Virtualized rendering active for pages outside current viewport `±1`.

#### 3. Intelligence Notebook Panel (`intelligence-panel.component.ts` & `.html`)
- **Typography & Aesthetics**: Slate dark/light surface tokens (`#0B0F17`, hairline borders `rgba(255,255,255,0.08)`), monospace code and table styling with JetBrains Mono.
- **Progressive Streamer**: Uses `fetch` + `ReadableStreamDefaultReader` with SSE text decoder to append tokens directly into DOM.
- **Citation Badges**: Renders interactive inline chips `[Page 4: 18V-36V DC]`. Clicking fires `DocumentSyncService.navigateTo({ page: 4, anchor: "18V-36V DC" })`.

#### 4. Command Palette (`command-palette.component.ts`)
- Omnipresent modal activated by `⌘K` / `Ctrl+K`.
- Features instant fuzzy match for switching ingested documents, jumping to specific page numbers, or running common queries.

---

## 4. Error Handling & Edge Cases

1. **PDF Range Chunk Failure**: If range request fails or backend does not support byte ranges, gracefully fall back to full arrayBuffer download with a progressive loading bar.
2. **Text Anchor Missing**: If citation anchor text is not found in the target page's text layer DOM, navigate to target page number and pulse an ambient illumination ring around the full page border.
3. **Stream Disconnects & Aborts**: Navigating away or submitting a new prompt triggers `AbortController.abort()`, cleanly closing the SSE connection and resetting active state without hanging.
4. **Window Resizing**: SVG bounding box overlay points re-compute dynamically using CSS vector transforms based on `zoomLevel * viewportRatio`.

---

## 5. Verification & Test Plan

### 5.1 Automated Backend Unit Tests
- `tests/test_document_raw.py`: Verify `GET /documents/{filename}/raw` returns correct `Content-Type: application/pdf`, `Accept-Ranges: bytes`, and handles partial byte requests (`Range: bytes=0-500`). Assert path traversal rejection with `400`.
- `tests/test_stream_endpoint.py`: Verify `POST /chat/stream` yields SSE headers `text/event-stream` and parses tokens and citation blocks.

### 5.2 Automated Frontend Tests
- `document-sync.service.spec.ts`: Verify dispatch and receipt of navigation and selection payloads.
- `pdf-canvas.component.spec.ts`: Test render task cancellation on zoom change and SVG highlight coordinate generation.
- `intelligence-panel.component.spec.ts`: Test token stream parsing and citation click handling.

### 5.3 Manual End-to-End Acceptance Verification
1. Launch backend (`uvicorn api:app`) and frontend (`ng serve`).
2. Verify dual-pane layout loads with PDF canvas taking left pane and chat notebook on right.
3. Submit query; verify tokens stream in progressively.
4. Click citation chip; verify left PDF viewer glides smoothly to cited page with ambient highlight.
5. Highlight phrase on PDF canvas; verify floating context action pill appears.
