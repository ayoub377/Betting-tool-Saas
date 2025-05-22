import { Component } from '@angular/core';
import {FirebaseuiAngularLibraryComponent} from "firebaseui-angular";
import {FooterComponent} from "../shared/footer/footer.component";
import {NavbarComponent} from "../shared/navbar/navbar.component";

@Component({
  selector: 'app-signup',
  standalone: true,
  imports: [
    FirebaseuiAngularLibraryComponent,
    FooterComponent,
    NavbarComponent
  ],
  template:`
<div class="min-h-screen flex flex-col bg-gray-100">
  <!-- Navbar -->
  <app-navbar></app-navbar>

  <!-- Main Content -->
  <div class="flex-grow flex items-center justify-center">
    <div class="bg-white shadow-lg rounded-lg p-8 max-w-md w-full">
      <h2 class="text-2xl font-semibold text-center text-gray-800 mb-4">
        Sign In / Sign Up
      </h2>
      <!-- Logo -->
      <div class="flex justify-center mb-6">
        <img
          src="assets/logo-saas.jpg"
          alt="SaaS Logo"
          class="h-16 w-auto md:h-20 lg:h-24 max-w-full object-contain"
        />
      </div>
      <!-- Firebase UI -->
      <firebase-ui></firebase-ui>
    </div>
  </div>

  <!-- Footer -->
  <app-footer></app-footer>
</div>


  `,
  styleUrl: './signup.component.css'
})
export class SignupComponent {

}
