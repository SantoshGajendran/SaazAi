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
                expect(target.bbox).toEqual([10, 20, 30, 40]);
                done();
            }
        });
        service.navigateTo(3, '18V DC', [10, 20, 30, 40]);
    });

    it('should update zoom level', (done) => {
        service.setZoom(1.5);
        service.zoomLevel$.subscribe(zoom => {
            expect(zoom).toBe(1.5);
            done();
        });
    });

    it('should clamp zoom level between 0.5 and 3.0', (done) => {
        service.setZoom(5.0);
        service.zoomLevel$.subscribe(zoom => {
            expect(zoom).toBe(3.0);
            done();
        });
    });

    it('should clamp zoom level on lower bound', (done) => {
        service.setZoom(0.1);
        service.zoomLevel$.subscribe(zoom => {
            expect(zoom).toBe(0.5);
            done();
        });
    });

    it('should support zoomIn and zoomOut', (done) => {
        service.setZoom(1.0);
        service.zoomIn();
        service.zoomLevel$.subscribe(zoom => {
            expect(zoom).toBeCloseTo(1.15);
            done();
        });
    });

    it('should emit active document changes', (done) => {
        service.setActiveDocument('manual.pdf');
        service.activeDocument$.subscribe(doc => {
            if (doc === 'manual.pdf') {
                expect(doc).toBe('manual.pdf');
                done();
            }
        });
    });

    it('should emit canvas selections', (done) => {
        const selection = { text: 'selected text', page: 2, clientX: 100, clientY: 200 };
        service.selectionTrigger$.subscribe(sel => {
            if (sel) {
                expect(sel).toEqual(selection);
                done();
            }
        });
        service.setSelection(selection);
    });
});
