import { Component, Inject, OnDestroy, OnInit } from '@angular/core';
import { AsyncPipe, DOCUMENT, NgIf } from '@angular/common';
import { AuthService } from '../services/auth.service';
import { Observable, Subscription } from 'rxjs';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-auth-button',
  template: `
<ng-container *ngIf="isAuthenticated$ | async as isAuthenticated; else loggedOut">
  <div *ngIf="isAuthenticated" class="relative inline-block text-white">
    <!-- Profile Button -->
    <div
      class="flex items-center cursor-pointer space-x-2 text-lg hover:text-gray-300 transition duration-300"
      (click)="toggleDropdown()"
      aria-label="User menu"
    >
      <span>{{ userName || 'User' }}</span>
      <svg
        xmlns="http://www.w3.org/2000/svg"
        class="h-5 w-5 transition-transform duration-300"
        [class.rotate-180]="dropdownOpen"
        fill="none"
        viewBox="0 0 24 24"
        stroke="currentColor"
        stroke-width="2"
      >
        <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7" />
      </svg>
    </div>

    <!-- Dropdown Menu -->
    <div
      *ngIf="dropdownOpen"
      class="absolute right-0 mt-2 w-48 bg-white text-gray-900 border border-gray-200 rounded-lg shadow-lg transition-opacity duration-200 opacity-100"
    >
      <button
        class="block w-full px-8 py-2 text-left text-sm hover:bg-gray-100 transition duration-300"
        (click)="logout()"
      >
        Log out
      </button>
    </div>
  </div>
</ng-container>

<!-- Logged Out State -->
<ng-template #loggedOut>
  <button class="bg-white text-blue-900 px-4 py-2 rounded-lg font-medium hover:bg-gray-200 transition" routerLink="/login">
    Log in
  </button>
</ng-template>
  `,
  standalone: true,
  imports: [NgIf, AsyncPipe, RouterLink],
})
export class AuthButtonComponent implements OnInit, OnDestroy {
  isAuthenticated$: Observable<boolean>;
  dropdownOpen = false;
  userName?: string;
  private authSubscription?: Subscription;

  constructor(@Inject(DOCUMENT) public document: Document, private auth: AuthService) {
    this.isAuthenticated$ = this.auth.isLogged();
  }

  ngOnInit(): void {
    this.authSubscription = this.auth.user$.subscribe((user) => {
      this.userName = user?.displayName || 'User';
    });
  }

  ngOnDestroy(): void {
    this.authSubscription?.unsubscribe(); // Prevent memory leaks
  }

  logout(): void {
    this.auth.logout();
  }

  toggleDropdown(): void {
    this.dropdownOpen = !this.dropdownOpen;
  }
}
