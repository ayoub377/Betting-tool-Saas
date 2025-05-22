import { Component } from '@angular/core';
import {FormsModule} from "@angular/forms";
import {NgIf} from "@angular/common";
import {getAuth, sendPasswordResetEmail, signInWithEmailAndPassword} from "@angular/fire/auth";
import {RouterLink} from "@angular/router";

@Component({
  selector: 'app-signin',
  standalone: true,
  imports: [
    FormsModule,
    NgIf,
    RouterLink
  ],
  templateUrl: './signin.component.html',
  styleUrl: './signin.component.css'
})
export class SigninComponent {
  email: string = '';
  password: string = '';
  errorMessage: string = '';

  onSignIn() {
    const auth = getAuth();
    signInWithEmailAndPassword(auth, this.email, this.password)
      .then((userCredential) => {
        // Signed in successfully
        const user = userCredential.user;
        console.log('User signed in:', user);
      })
      .catch((error) => {
        // Handle errors
        this.errorMessage = error.message;
        console.error('Error signing in:', error);
      });
  }

onForgotPassword() {
  const auth = getAuth();
  sendPasswordResetEmail(auth, this.email)
    .then(() => {
      alert('Password reset email sent. Check your inbox.');
    })
    .catch((error) => {
      this.errorMessage = error.message;
      console.error('Error sending password reset email:', error);
    });
}
}
