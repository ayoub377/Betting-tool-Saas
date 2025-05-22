import { Injectable } from '@angular/core';
import { CanActivate, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';
import { Observable } from 'rxjs';
import { tap, map } from 'rxjs/operators';
import {AngularFireAuth} from "@angular/fire/compat/auth";

@Injectable({
  providedIn: 'root',
})
export class AuthGuard implements CanActivate {
  constructor(private afAuth: AngularFireAuth, private router: Router) {}

  canActivate(): Observable<boolean> {
    return this.afAuth.authState.pipe(
      map((user) => !!user), // Check if a user is logged in
      tap((isLoggedIn) => {
        if (!isLoggedIn) {
          this.router.navigate(['/']); // Redirect to home page if not logged in
        }
      })
    );
  }
}
