import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import {catchError, Observable} from 'rxjs';
import {Match} from '../models/match';
import {AuthService as AuthService_} from "./auth.service";
import {environment} from "../../environments/environment";

@Injectable({
  providedIn: 'root'
})

export class LeagueService {
  private apiUrl =  environment.apiUrl;

  constructor(private http: HttpClient, private auth: AuthService_) { }

  // Example method to fetch all leagues
  getMatchesAndOdds(leagues: string, bookmakers: string[], allMatches: boolean): Observable<Match[]> {
  let token = this.auth.accessToken;
  let headers = { headers: { Authorization: `Bearer ${token}` } };

  return this.http.get<Match[]>(`${this.apiUrl}/odds/odds/${leagues}`, {  // Leagues in path
    ...headers,
    params: {
      bookmakers: bookmakers.join(','),  // Query parameter
      allMatches: allMatches.toString()  // Convert boolean to string for proper API handling
    }
  });
}

  // implmenet a call to calculate ev function
    calculateEV(matches:Match[]): Observable<{ ev: number }> {
      let token = this.auth.accessToken;
      let headers = { headers: { Authorization: `Bearer ${token}` } };
      return this.http.post<{ ev: number }>(`${this.apiUrl}/odds/odds/calculate-ev/${matches}`,
        {
          ...headers,
          params:{
            matches:matches
          }
        } ).pipe(
        catchError((err) => {
          console.error('Error calculating EV:', err);
          throw err;
        })
      );
    }


}
