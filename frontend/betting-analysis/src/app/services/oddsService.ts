import { Injectable } from '@angular/core';
import {BehaviorSubject, catchError, Observable} from 'rxjs';
import {LeagueService} from "./league.service";
import {Match} from "../models/match";
import {tap} from "rxjs/operators"; // Import your OddsData interface

@Injectable({
  providedIn: 'root'
})

export class OddsService {
  private oddsDataSubject: BehaviorSubject<Match[] | null> = new BehaviorSubject<Match[] | null>(null);

  constructor(private leagueService: LeagueService) {}

fetchOddsData(leagues: string, bookmakers: string[], allMatches: boolean): Observable<any> {
  return this.leagueService.getMatchesAndOdds(leagues, bookmakers, allMatches).pipe(
    tap((data) => {
      this.oddsDataSubject.next(data);
    }),
    catchError((err) => {
      console.error('Error fetching odds data:', err);
      throw err;
    })
  );
}
  setOddsData(data: Match[]): void {
    this.oddsDataSubject.next(data); // Optionally set data directly if needed
  }


}
