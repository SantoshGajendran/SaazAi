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
