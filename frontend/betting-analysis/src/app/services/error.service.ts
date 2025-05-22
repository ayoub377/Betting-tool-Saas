import { Injectable } from '@angular/core';
import {HttpErrorResponse} from "@angular/common/http";
import {Subject} from "rxjs";
import {MatDialog} from "@angular/material/dialog";
import {ErrorDialogComponent} from "../shared/error-dialog/error-dialog.component";

@Injectable({
  providedIn: 'root',
})
export class ErrorService {
  constructor(private dialog: MatDialog) {}
  handleError(error: any): void {
    if (error instanceof HttpErrorResponse) {
      switch (error.status) {
        case 401:
          this.handleUnauthorizedError();
          break;
        case 403:
          this.handleForbiddenError();
          break;
        case 400:
          this.handleBadRequestError(error);
          break;
        case 429:
          this.handleRateLimitError();
          break;
        case 500:
          this.handleServerError();
          break;
        default:
          this.handleGenericError(error);
      }
    } else {
      this.handleGenericError(error);
    }
  }
  handleUnauthorizedError(): void {
    this.openErrorDialog('Unauthorized Access', 'You are not authorized to access this resource. Please log in again.');
    // Optionally, redirect to login page or perform logout
  }

  handleForbiddenError(): void {
    this.openErrorDialog('Access Denied', 'You do not have permission to access this resource.');
  }

  handleBadRequestError(error: any): void {
    const message = error.error?.message || 'Invalid request. Please check your input.';
    this.openErrorDialog('Bad Request', message);
  }

  handleRateLimitError(): void {
    this.openErrorDialog('Rate Limit Exceeded', 'You have exceeded the allowed number of requests. Please try again later.');
  }

  handleServerError(): void {
    this.openErrorDialog('Server Error', 'An internal server error occurred. Please try again later.');
  }

  handleGenericError(error: any): void {
    const message = error.error?.message || 'An unexpected error occurred.';
    this.openErrorDialog('Error', message);
  }

  private openErrorDialog(title: string, message: string): void {
    this.dialog.open(ErrorDialogComponent, {
      data: { title, message },
      width: '400px',
    });
  }
}
