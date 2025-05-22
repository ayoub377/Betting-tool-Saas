import {Component, OnInit} from '@angular/core';
import {RouterLink, RouterOutlet} from '@angular/router';
import {Analytics, getAnalytics, logEvent} from "@angular/fire/analytics";
import {initializeApp} from "@angular/fire/app";
import {environment} from "../environments/environment";

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, RouterLink],
  templateUrl: './app.component.html',
  styleUrl: './app.component.css'
})
export class AppComponent implements OnInit{
  title = 'betting-analysis';
  constructor(private analytics: Analytics) {}
  ngOnInit(): void {
    logEvent(this.analytics,'app-starting')
  }

}
