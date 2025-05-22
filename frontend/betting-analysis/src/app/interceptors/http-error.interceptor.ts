import {
  HttpErrorResponse,
  HttpEvent,
  HttpHandler,
  HttpInterceptor,
  HttpRequest
} from '@angular/common/http';
import {Injectable} from "@angular/core";
import {catchError, Observable, throwError} from "rxjs";
import {ErrorService} from "../services/error.service";

@Injectable()
export class HttpErrorInterceptor implements HttpInterceptor {
  constructor(private errorService: ErrorService) {}

  intercept(req: HttpRequest<any>, next: HttpHandler): Observable<HttpEvent<any>> {
    return next.handle(req).pipe(
      catchError((error: HttpErrorResponse) => {
        if (error instanceof HttpErrorResponse) {
          // Handle specific HTTP errors
          this.handleError(error);
        }
        return throwError(() => error); // Propagate the error to the caller
      })
    );
  }

  private handleError(error: HttpErrorResponse): void {
    switch (error.status) {
      case 401:
        this.errorService.handleUnauthorizedError();
        break;
      case 403:
        this.errorService.handleForbiddenError();
        break;
      case 400:
        this.errorService.handleBadRequestError(error);
        break;
      case 429:
        this.errorService.handleRateLimitError();
        break;
      case 500:
        this.errorService.handleServerError();
        break;
      default:
        this.errorService.handleGenericError(error);
    }
  }
}
