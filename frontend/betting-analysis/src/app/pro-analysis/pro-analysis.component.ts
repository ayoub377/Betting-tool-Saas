import {Component, OnInit} from '@angular/core';
import {ActivatedRoute} from "@angular/router";
import {AnalysisServices} from "../services/analysisServices";
import {FormBuilder, FormGroup, ReactiveFormsModule, Validators} from "@angular/forms";
import {JsonPipe, NgIf} from "@angular/common";
import {MatFormFieldModule} from "@angular/material/form-field";
import {MatInputModule} from "@angular/material/input";
import {MatButtonModule} from "@angular/material/button";
import {ErrorDialogComponent} from "../shared/error-dialog/error-dialog.component";
import {MatDialog} from "@angular/material/dialog";
import {MatProgressSpinner} from "@angular/material/progress-spinner";
import {NavbarComponent} from "../shared/navbar/navbar.component";
import {FooterComponent} from "../shared/footer/footer.component";
import {MatCard, MatCardContent} from "@angular/material/card";
import {
  MatCell, MatCellDef,
  MatColumnDef,
  MatHeaderCell,
  MatHeaderCellDef,
  MatHeaderRow, MatHeaderRowDef,
  MatRow, MatRowDef,
  MatTable
} from "@angular/material/table";
import {MarketValuePipe} from "../market-value.pipe";
import {ComparisonItem} from "../models/pro-analysis";
import {catchError, of} from "rxjs";
import {ErrorService} from "../services/error.service";


@Component({
  selector: 'app-pro-analysis',
  standalone: true,
  imports: [
    NgIf,
    ReactiveFormsModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    JsonPipe,
    MatProgressSpinner,
    NavbarComponent,
    FooterComponent,
    MatCard,
    MatCardContent,
    MatHeaderRow,
    MatRow,
    MatHeaderCell,
    MatCell,
    MatTable,
    MatColumnDef,
    MatHeaderCellDef,
    MatCellDef,
    MatHeaderRowDef,
    MatRowDef,
    MarketValuePipe,
  ],
  templateUrl: './pro-analysis.component.html',
  styleUrl: './pro-analysis.component.css'
})


export class ProAnalysisComponent implements OnInit{
  home_team: string | null = null;
  away_team: string | null = null;
  comparisonData: any;
  insights: string | null=null;

  teamForm: FormGroup;
  isLoading = false; // Add this line

  constructor(
    private route: ActivatedRoute,
    private analysisService: AnalysisServices,
    private errorService:ErrorService,
    private fb: FormBuilder
  ) {
    // Initialize the form
    this.teamForm = this.fb.group({
      home_team: ['', Validators.required],
      away_team: ['', Validators.required]
    });
  }

  ngOnInit(): void {
    // Subscribe to route parameters
    this.route.params.subscribe((params) => {
      this.home_team = params['home_team'] || null;
      this.away_team = params['away_team'] || null;

      // Pre-populate the form if parameters are provided
      if (this.home_team && this.away_team) {
        this.teamForm.patchValue({
          home_team: this.home_team,
          away_team: this.away_team
        });
      }
    });
  }

  onSubmit(): void {
    this.isLoading = true;
    if (this.teamForm.valid) {
      const { home_team, away_team } = this.teamForm.value;
      this.fetchComparisonData(home_team, away_team);
    } else {
      console.error('Form is invalid.');
    }
  }

fetchComparisonData(home_team: string, away_team: string): void {this.home_team = home_team
  this.away_team = away_team
  this.isLoading = true; // Show spinner while loading
  this.analysisService.getComparaison(home_team, away_team).subscribe(
    (data) => {
      console.log('API Response:', data); // Debug the raw API response

      this.isLoading = false; // Hide spinner

      if (data && Array.isArray(data.comparison)) {
        // Pass the comparison array to the formatting function
        this.comparisonData = this.formatComparisonData(data.comparison);
      } else {
        this.comparisonData = this.formatComparisonData(data);
      }
    },
    (err) => {
      this.isLoading = false; // Hide spinner
      // Use ErrorService to handle the error
      this.errorService.handleError(err);
      return of(null); // Return a null Observable to prevent further propagation
    }
  );
}

  private formatComparisonData(comparison: ComparisonItem[]): any[] {
    return comparison.map((item) => ({
      position: item.position,
      homePlayer: item.home_player
        ? {
            name: item.home_player.name,
            jersey: item.home_player.jersey_number,
            value: item.home_player.market_value,
          }
        : null,
      awayPlayer: item.away_player
        ? {
            name: item.away_player.name,
            jersey: item.away_player.jersey_number,
            value: item.away_player.market_value,
          }
        : null,
    }));
  }

}
