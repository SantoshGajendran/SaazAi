import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

export interface ChatResponse {
    response: string;
    image_base64?: string;
    citations: string[];
}

export interface DocumentResponse {
    documents: string[];
}

@Injectable({
    providedIn: 'root'
})
export class ApiService {
    private apiUrl = 'http://localhost:8000';

    constructor(private http: HttpClient) { }

    getDocuments(): Observable<DocumentResponse> {
        return this.http.get<DocumentResponse>(`${this.apiUrl}/documents`);
    }

    getStats(): Observable<{ count: number; total_size: string }> {
        return this.http.get<{ count: number; total_size: string }>(`${this.apiUrl}/stats`);
    }

    uploadDocument(file: File): Observable<any> {
        const formData = new FormData();
        formData.append('file', file);
        return this.http.post(`${this.apiUrl}/upload`, formData);
    }

    deleteDocument(filename: string): Observable<any> {
        return this.http.delete(`${this.apiUrl}/documents/${filename}`);
    }

    chat(query: string, selectedFile: string): Observable<ChatResponse> {
        return this.http.post<ChatResponse>(`${this.apiUrl}/chat`, {
            query: query,
            selected_file: selectedFile
        });
    }

    getUploadStatus(filename: string): Observable<{ filename: string; status: string }> {
        return this.http.get<{ filename: string; status: string }>(`${this.apiUrl}/upload_status/${filename}`);
    }
}
