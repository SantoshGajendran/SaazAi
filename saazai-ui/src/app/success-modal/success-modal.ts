import { Component, EventEmitter, Output } from '@angular/core';

@Component({
  selector: 'app-success-modal',
  standalone: true,
  imports: [],
  templateUrl: './success-modal.html',
  styleUrl: './success-modal.css' // Use styleUrl (singular) for Angular 17+
})
export class SuccessModalComponent {
  @Output() onClose = new EventEmitter<void>();

  close() {
    this.onClose.emit();
  }
}
