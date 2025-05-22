import { Component } from '@angular/core';
import {NgClass, NgIf, NgOptimizedImage} from "@angular/common";
import {AuthService} from "../../services/auth.service";
import {AuthButtonComponent} from "../../auth/auth.component";

@Component({
  selector: 'app-navbar',
  standalone: true,
  imports: [
    NgIf,
    NgOptimizedImage,
    AuthButtonComponent,
    NgClass
  ],
  templateUrl: './navbar.component.html',
  styleUrl: './navbar.component.css'
})

export class NavbarComponent {
  isMenuOpen = false; // Controls the visibility of the mobile menu
  isMobileDropdownOpen = false; // Controls the mobile dropdown
  isDesktopDropdownOpen = true; // Controls the desktop dropdown
  dropdownTimeout: any; // Timeout for dropdown delay

  constructor() {
  }

  toggleResponsive() {
    this.isMenuOpen = !this.isMenuOpen; // Toggle the mobile menu
    this.isMobileDropdownOpen = false; // Close the mobile dropdown when menu toggles
  }

  toggleMobileDropdown() {
    this.isMobileDropdownOpen = !this.isMobileDropdownOpen;
  }

  openDesktopDropdown() {
    clearTimeout(this.dropdownTimeout); // Cancel any pending close
    this.isDesktopDropdownOpen = true; // Open desktop dropdown on hover
  }

  closeDesktopDropdown() {
    this.dropdownTimeout = setTimeout(() => {
      this.isDesktopDropdownOpen = false; // Close dropdown after delay
    }, 200); // Delay in milliseconds
  }

  scrollToServices() {
    const servicesSection = document.getElementById('services');
    if (servicesSection) {
      servicesSection.scrollIntoView({ behavior: 'smooth' });
    }
  }

}
