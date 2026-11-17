import { Component, ElementRef, ViewChild, AfterViewChecked, OnInit, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService, ChatResponse } from '../api.service';
import { MarkdownModule } from 'ngx-markdown';
import { ActivatedRoute } from '@angular/router';

interface Message {
    role: 'user' | 'assistant';
    content: string;
    image?: string;
    citations?: string[];
    expandedSources?: boolean;
    expandedImage?: boolean;
}

@Component({
    selector: 'app-chat',
    standalone: true,
    imports: [CommonModule, FormsModule, MarkdownModule],
    templateUrl: './chat.component.html',
    styleUrl: './chat.component.css'
})
export class ChatComponent implements OnInit, AfterViewChecked {
    @ViewChild('scrollContainer') private scrollContainer!: ElementRef;

    selectedFile: string | null = null;
    messages: Message[] = [];
    userInput: string = '';
    isLoading: boolean = false;

    constructor(private api: ApiService, private route: ActivatedRoute, private cdr: ChangeDetectorRef) { }

    ngOnInit(): void {
        this.route.queryParams.subscribe(params => {
            const file = params['file'];
            if (file && file !== this.selectedFile) {
                this.selectedFile = file;
                this.messages = []; // Reset on file change
            }
        });
    }

    ngAfterViewChecked() {
        this.scrollToBottom();
    }

    scrollToBottom(): void {
        try {
            this.scrollContainer.nativeElement.scrollTop = this.scrollContainer.nativeElement.scrollHeight;
        } catch (err) { }
    }

    sendMessage() {
        if (!this.userInput.trim() || !this.selectedFile) return;

        const query = this.userInput;
        this.userInput = ''; // Clear input

        // Add User Message
        this.messages.push({ role: 'user', content: query });
        this.isLoading = true;

        this.api.chat(query, this.selectedFile).subscribe({
            next: (res: ChatResponse) => {
                this.messages.push({
                    role: 'assistant',
                    content: res.response,
                    image: res.image_base64,
                    citations: res.citations
                });
                this.isLoading = false;
                this.cdr.detectChanges(); // Force UI Update
            },
            error: (err) => {
                console.error('Chat Error:', err);
                this.messages.push({ role: 'assistant', content: 'Error: ' + err.message });
                this.isLoading = false;
                this.cdr.detectChanges(); // Force UI Update
            }
        });
    }
}
