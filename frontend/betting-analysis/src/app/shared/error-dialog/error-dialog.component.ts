import {Component, Inject} from '@angular/core';
import {
  MAT_DIALOG_DATA,
  MatDialogActions,
  MatDialogClose,
  MatDialogContent,
  MatDialogTitle
} from "@angular/material/dialog";
import {MatButton, MatIconButton} from "@angular/material/button";
import {MatIcon} from "@angular/material/icon";

@Component({
  selector: 'app-error-dialog',
  standalone: true,
  imports: [
    MatDialogContent,
    MatDialogActions,
    MatDialogClose,
    MatButton,
    MatDialogTitle,
    MatIcon,
    MatIconButton
  ],
  template: `
    <div class="dialog-header">
      <h2 mat-dialog-title>Error</h2>
      <button mat-icon-button class="close-button px-5" mat-dialog-close>
        <mat-icon class="close-icon">close</mat-icon>
      </button>
    </div>
    <mat-dialog-content>
      {{ data.message }}
    </mat-dialog-content>
    <mat-dialog-actions>
      <button mat-button class="close-dialog-button" mat-dialog-close>Close</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }

      .close-button {
        color: #ff0000; /* Red color for the X mark */
      }

      .close-icon {
        font-size: 24px;
      }

      .close-dialog-button {
        color: #ff0000; /* Red color for the close button */
      }

      .dialog-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
      }
      .close-button {
        color: #ff0000; /* Red color for the X mark */
      }
      .close-icon {
        font-size: 24px;
      }
      .close-dialog-button {
        color: #ff0000; /* Red color for the close button */
      }
    `,
  ],
  styleUrl: './error-dialog.component.css'
})
export class ErrorDialogComponent {
    constructor(@Inject(MAT_DIALOG_DATA) public data: { message: string }) {}

}
