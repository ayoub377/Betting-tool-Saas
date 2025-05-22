import {catchError, Observable, retry, throwError} from "rxjs";
import {HttpClient, HttpErrorResponse} from "@angular/common/http";
import {Injectable} from "@angular/core";
import {AuthService as AuthService_} from "./auth.service"
import {MatchComparison} from "../models/pro-analysis";
import {environment} from "../../environments/environment";

@Injectable({
  providedIn: 'root'
})

export class AnalysisServices {
  private apiUrl = environment.apiUrl; // Replace with your backend URL
  constructor(private http: HttpClient,private auth: AuthService_){}

getComparaison(homeTeam: string, awayTeam: string): Observable<any> {
    let token = this.auth.accessToken;
    let headers = {
        headers: { Authorization: `Bearer ${token}` },
    };
    const url = `${this.apiUrl}/clubs/compare/${homeTeam}/${awayTeam}`;

    return this.http.get<MatchComparison>(url, headers).pipe(
        retry(3), // Retry the request up to 3 times
        catchError((error) => {
            // Handle the error after retries have been exhausted
            console.error('Error after retries:', error);
            return throwError(() => new Error('An error occurred after retrying the request.'));
        })
    );
}

}
