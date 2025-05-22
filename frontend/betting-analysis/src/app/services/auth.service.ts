import { Injectable } from '@angular/core';
import { Auth, signInWithPopup, GoogleAuthProvider, signOut, onAuthStateChanged, getIdToken } from '@angular/fire/auth';
import { BehaviorSubject, Observable } from 'rxjs';
import {routes} from "../app.routes";
import {Router} from "@angular/router";

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  private userSubject = new BehaviorSubject<any>(null); // For user information
  private isAuthenticatedSubject = new BehaviorSubject<boolean>(false); // For auth state
  accessToken?: string;

  user$: Observable<any> = this.userSubject.asObservable(); // Observable for user information
  isAuthenticated$: Observable<boolean> = this.isAuthenticatedSubject.asObservable(); // Observable for auth state

  constructor(private auth: Auth,private router: Router) {
    // Monitor auth state changes
    onAuthStateChanged(this.auth, (user) => {
      if (user) {
        this.isAuthenticatedSubject.next(true);
        this.userSubject.next(user); // Update user information
        this.fetchAccessToken(); // Fetch access token
      } else {
        this.isAuthenticatedSubject.next(false);
        this.userSubject.next(null);
        this.accessToken = undefined;
      }
    });
  }

  login(): void {
    const provider = new GoogleAuthProvider(); // Use Google as the provider
    signInWithPopup(this.auth, provider).catch((err) => {
      console.error('Login failed:', err);
    });
  }

  logout(): void {
    signOut(this.auth).then((r)=>{
      console.log('logout successful')
      this.router.navigateByUrl('/').then(r => console.log("redirected!"));
    }).catch((err) => {
      console.error('Logout failed:', err);
    });
  }

  isLogged(): Observable<boolean> {
    return this.isAuthenticated$; // Return auth state as observable
  }

fetchAccessToken(): void {
  const user = this.auth.currentUser; // Get the current user from Firebase Auth

  if (user) {
    user.getIdToken(true) // Force refresh the token
      .then((token) => {
        this.accessToken = token; // Save the token
      })
      .catch((err) => {
        console.error('Failed to fetch access token:', err);
      });
  } else {
    console.warn('No authenticated user found.');
  }
}

}
