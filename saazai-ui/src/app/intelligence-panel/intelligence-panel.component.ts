import { Component, OnInit, OnDestroy, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MarkdownModule } from 'ngx-markdown';
import { DocumentSyncService } from '../services/document-sync.service';
import { Subscription } from 'rxjs';

export interface Citation {
    file: string;
    page: number;
    anchor: string;
    score: number;
}

export interface MessageItem {
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
                    this.abortActiveStream();
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

            if (!res.ok) {
                const errorText = await res.text();
                throw new Error(`HTTP ${res.status}: ${errorText}`);
            }

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
                    const cleanChunk = chunk.replace(/\r/g, '').trim();
                    if (cleanChunk.startsWith('event: token')) {
                        const jsonStr = cleanChunk.replace(/^event:\s*token\s*\ndata:\s*/, '');
                        try {
                            const data = JSON.parse(jsonStr);
                            if (data && data.delta !== undefined) {
                                assistantMsg.content += data.delta;
                                this.cdr.detectChanges();
                            }
                        } catch (e) {
                            console.error('Failed to parse token SSE payload:', jsonStr, e);
                        }
                    } else if (cleanChunk.startsWith('event: citation')) {
                        const jsonStr = cleanChunk.replace(/^event:\s*citation\s*\ndata:\s*/, '');
                        try {
                            const cite = JSON.parse(jsonStr);
                            if (!assistantMsg.citations) assistantMsg.citations = [];
                            assistantMsg.citations.push(cite);
                            this.cdr.detectChanges();
                        } catch (e) {
                            console.error('Failed to parse citation SSE payload:', jsonStr, e);
                        }
                    } else if (cleanChunk.startsWith('event: error')) {
                        const jsonStr = cleanChunk.replace(/^event:\s*error\s*\ndata:\s*/, '');
                        try {
                            const err = JSON.parse(jsonStr);
                            assistantMsg.content += `\n\n*[Error: ${err.message}]*`;
                            this.cdr.detectChanges();
                        } catch (e) {
                            console.error('Failed to parse error SSE payload:', jsonStr, e);
                        }
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
