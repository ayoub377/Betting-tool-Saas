import {Component, HostListener} from '@angular/core';

import {NavbarComponent} from "../shared/navbar/navbar.component";
import {FooterComponent} from "../shared/footer/footer.component";
import {Router, RouterLink} from "@angular/router";
import {FaqComponent} from "../faq/faq.component";
import {AboutUsComponent} from "../about-us/about-us.component";
import {FormsModule} from "@angular/forms";
import {NgIf} from "@angular/common";
import {HttpClient} from "@angular/common/http";

@Component({
  selector: 'app-home',
  standalone: true,
  imports: [
    NavbarComponent,
    FooterComponent,
    FaqComponent,
    RouterLink,
    FormsModule,
    NgIf,

  ],
  templateUrl: './home.component.html',
  styleUrl: './home.component.css'
})
export class HomeComponent {
  bannerOpacity = 1; // Initial opacity
  bannerTransform = 0; // Initial translation for smooth fading
  servicesOpacity: number = 0;
  servicesTransform: number = 50;
  aboutOpacity = 1;
  aboutTransform = 0;
  waitlistEmail: string = '';
  waitlistSuccess: boolean = false;

constructor(private router:Router,private http:HttpClient) {
}
  onWaitlistSubmit(): void {
  const ApiUrl="http://localhost:9000"
    const payload = { email: this.waitlistEmail };

    this.http.post(`${ApiUrl}/api/waitlist`, payload).subscribe(
      (response) => {
        this.waitlistSuccess = true;
      },
      (error) => {
        console.error('Error adding to waitlist:', error);
      }
    );
  }

  @HostListener('window:scroll', [])
  onWindowScroll_banner() {
    const scrollY = window.scrollY;

    // Banner fade logic
    this.bannerOpacity = Math.max(1 - scrollY / 400, 0);
    this.bannerTransform = Math.min(scrollY / 5, 50);

    // Services fade logic
    const servicesSection = document.getElementById('services');
    if (servicesSection) {
      const servicesTop = servicesSection.getBoundingClientRect().top;
      const windowHeight = window.innerHeight;

      if (servicesTop < windowHeight - 100) {
        this.servicesOpacity = 1;
        this.servicesTransform = 0;
      } else {
        this.servicesOpacity = 0;
        this.servicesTransform = 50;
      }
    }
  }

  @HostListener('window:scroll', ['$event'])
  onScroll() {
    const scrollTop = window.scrollY;
    const windowHeight = window.innerHeight;

    // Handle About Section
    const aboutSection = document.getElementById('about');
    if (aboutSection) {
      const aboutOffsetTop = aboutSection.offsetTop;
      if (scrollTop + windowHeight > aboutOffsetTop && scrollTop < aboutOffsetTop + aboutSection.offsetHeight) {
        this.aboutOpacity = 1; // Fully visible
        this.aboutTransform = 0; // No transform
      } else {
        this.aboutOpacity = 0; // Hidden
        this.aboutTransform = 50; // Slightly moved down
      }
    }

    // Handle Services Section
    const servicesSection = document.getElementById('services');
    if (servicesSection) {
      const servicesOffsetTop = servicesSection.offsetTop;
      if (scrollTop + windowHeight > servicesOffsetTop && scrollTop < servicesOffsetTop + servicesSection.offsetHeight) {
        this.servicesOpacity = 1; // Fully visible
        this.servicesTransform = 0; // No transform
      } else {
        this.servicesOpacity = 0; // Hidden
        this.servicesTransform = 50; // Slightly moved down
      }
    }
  }

  navigateToRoute() {
  this.router.navigate(['/real-time-odds']).then(r => console.log(r)); // Replace '/your-route' with the actual route you want to navigate to
}
  navigateToLineups() {
  this.router.navigate(['/pro-analysis']).then(r => console.log(r)); // Replace '/your-route' with the actual route you want to navigate to
}

  protected readonly AboutUsComponent = AboutUsComponent;
}
