import {Component} from '@angular/core';
import {AsyncPipe, DatePipe, NgForOf, NgIf, NgOptimizedImage, TitleCasePipe} from "@angular/common";
import {FormBuilder, FormGroup, FormsModule, ReactiveFormsModule, Validators} from "@angular/forms";
import {catchError, Observable, of, Subscription} from "rxjs";
import {Match} from "../models/match";
import {OddsService} from "../services/oddsService";
import {RouterLink} from "@angular/router";
import {NavbarComponent} from "../shared/navbar/navbar.component";
import {FooterComponent} from "../shared/footer/footer.component";
import {MatDialog} from "@angular/material/dialog";
import {ErrorDialogComponent} from "../shared/error-dialog/error-dialog.component";
import {tap} from "rxjs/operators";
import {MatTooltip} from "@angular/material/tooltip";
import {ErrorService} from "../services/error.service";
import {MatError, MatFormField, MatHint, MatLabel} from "@angular/material/form-field";
import {MatOption, MatSelect} from "@angular/material/select";
import {MatButton} from "@angular/material/button";
import {MatCheckbox} from "@angular/material/checkbox";
import {LeagueService} from "../services/league.service";


@Component({
  selector: 'app-realtimeodds',
  standalone: true,
  imports: [
    AsyncPipe,
    DatePipe,
    FormsModule,
    NgForOf,
    NgIf,
    TitleCasePipe,
    RouterLink,
    NavbarComponent,
    FooterComponent,
    MatTooltip,
    MatFormField,
    ReactiveFormsModule,
    MatSelect,
    MatOption,
    MatLabel,
    MatError,
    MatHint,
    MatButton,
    NgOptimizedImage,
    MatCheckbox
  ],
  templateUrl: './realtimeodds.component.html',
  styleUrl: './realtimeodds.component.css'
})

export class RealtimeoddsComponent {
  oddsData$: Observable<Match[] | null> | null=null; // Expose as an Observable of OddsData
  isLoading = false;
  leagues = [
    { value: 'soccer_netherlands_eredivisie', label: 'Netherlands Eredivisie' },
    { value: 'soccer_poland_ekstraklasa', label: 'Poland Ekstraklasa' },
    { value: 'soccer_portugal_primeira_liga', label: 'Portugal Primeira Liga' },
    { value: 'soccer_spain_la_liga', label: 'Spain La Liga' },
    { value: 'soccer_spain_segunda_division', label: 'Spain Segunda Division' },
    { value: 'soccer_spl', label: 'Scottish Premier League' },
    { value: 'soccer_norway_eliteserien', label: 'Norway Eliteserien' },
    { value: 'soccer_germany_bundesliga', label: 'Germany Bundesliga' },
    { value: 'soccer_france_ligue_one', label: 'France Ligue One' },
    { value: 'soccer_epl', label: 'English Premier League' },
    { value: 'soccer_usa_mls', label: 'USA MLS' },
    { value: 'soccer_brazil_serie_b', label: 'Brazil Serie B' },
    { value: 'soccer_italy_serie_a', label: 'Italy Serie A' },
    { value: 'soccer_brazil_campeonato', label: 'Brazil Campeonato' },
    { value: 'soccer_argentina_primera_division', label: 'Argentina Primera Division' }
  ];
  bookmakers = ['Pinnacle', 'William Hill', 'Betclic', '1xBet', 'Suprabets', 'Everygame', 'Marathon Bet', 'BetOnline.ag', 'Nordic Bet', 'Betsson', 'Unibet', 'Betfair', 'Matchbook', 'GTbets'];
  selectedLeague: string = ''; // Holds the selected league ID
  dropdownOpen = false;
  allMatches: boolean = true
  selectedBookmaker: string[]=['Pinnacle'];  // Holds the selected bookmaker
  private errorSubscription!: Subscription;
  oddsForm: FormGroup;
  isNormalUser = false; // Change this based on user authentication
  matches_ : Match[] | null=null;

  constructor(private fb: FormBuilder, private oddsService: OddsService, private errorService: ErrorService,private leagueService:LeagueService) {
        this.oddsForm = this.fb.group({
      league: ['', Validators.required],
      bookmaker: [''],  // Bookmaker is optional
    });
  }

calculateEV() {
  if (this.isNormalUser) {
    alert('Upgrade to premium to access EV calculations.');
    return;
  }
  console.log("entering")

  this.leagueService.calculateEV(this.matches_!)

}

onSubmit(): void {
  this.isLoading = true;

  // Ensure Pinnacle is always included
  const selectedBookmakersWithPinnacle = this.selectedBookmaker.includes('Pinnacle')
    ? this.selectedBookmaker
    : [...this.selectedBookmaker, 'Pinnacle'];

  this.oddsData$ = this.oddsService.fetchOddsData(this.selectedLeague, selectedBookmakersWithPinnacle, this.allMatches).pipe(
    tap(() => {
      this.isLoading = false;
    }),
    catchError((err) => {
      this.isLoading = false;
      this.errorService.handleError(err);
      return of(null);
    })
  );
}

  toggleMatches() {
    this.allMatches = !this.allMatches;
    console.log('All Matches:', this.allMatches);
  }
  toggleDropdown() {
    this.dropdownOpen = !this.dropdownOpen;
  }

  selectLeague(league: string) {
    this.selectedLeague = league;
    this.dropdownOpen = false;
  }

  getSelectedLeagueName(): string | null {
  const selectedLeagueObj = this.leagues.find(league => league.value === this.selectedLeague);
  return selectedLeagueObj ? selectedLeagueObj.label : null;
}

  getLeagueLabel(value: string): string {
    const league = this.leagues.find(l => l.value === value);
    return league ? league.label : '';
  }
  protected readonly length = length;
  protected readonly console = console;

}
