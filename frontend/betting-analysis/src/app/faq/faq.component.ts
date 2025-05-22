import { Component, ElementRef, HostListener, OnDestroy, QueryList, ViewChildren} from '@angular/core';
import {NgForOf, NgIf} from "@angular/common";
import {animate, style, transition, trigger} from "@angular/animations";

@Component({
  selector: 'app-faq',
  standalone: true,
  imports: [
    NgForOf,
    NgIf
  ],
    animations: [
    trigger('fadeAnimation', [
      transition(':enter', [
        style({ opacity: 0 }),
        animate('300ms ease-in', style({ opacity: 1 })),
      ]),
      transition(':leave', [
        animate('300ms ease-out', style({ opacity: 0 })),
      ]),
    ]),
  ],
  templateUrl: './faq.component.html',
  styleUrl: './faq.component.css'
})

export class FaqComponent {
  isVisible = false;
  aboutOpacity = 1;
  aboutTransform = 0;

  // Track the open/close state of each FAQ item
  isOpen: boolean[] = [];

  faqItems = [
    { question: ' What is Sharper-Bets?',
      answer: 'Sharper-Bets is a platform designed to help sports bettors make more informed decisions by providing real-time odds ' +
        'from multiple bookmakers and comparing them to identify edges. We also remove the vigorish (vig) from Pinnacle odds, ' +
        'which are among the sharpest in the market. Additionally, we enable users to compare two teams’ starting lineups based on market value from Transfermarkt, ' +
        'giving bettors access to valuable asymmetric information, especially when teams are not well-known', open: false },
    { question: 'How does Sharper-Bets help me make better betting decisions?', answer: 'Our platform allows you to compare real-time odds from different bookmakers, helping you identify favorable bets. By removing the vig from Pinnacle odds, we provide a clearer view of true market value. We also allow you to compare the starting lineups of two teams based on their players\' market values, which helps you make better decisions when the teams are not familiar to you.', open: false },
    { question: 'How can I join the waiting list?', answer: 'To join the waiting list, simply visit add into the waiting list form in services section. You\'ll be notified when we open up the platform for broader access and receive early-bird pricing benefits.', open: false },
    { question: 'How do I compare odds between bookmakers?', answer: 'Once you sign up, you\'ll have access to a dashboard where you can view real-time odds from different bookmakers for the sports and events you\'re interested in.', open: false },
    { question: 'Can I see the market value of players in the lineup comparison?', answer: 'Yes! Our lineup comparison feature not only shows you the market value of players (powered by Transfermarkt) but also analyzes the current starting lineups of the match, comparing players position by position. This gives you a deeper understanding of team strengths and weaknesses. When combined with real-time odds and market sentiment, our system provides you with the insights needed to make smarter, more profitable decisions.', open: false },
    { question: 'What does “removing the vig from Pinnacle odds” mean, and why is it important?', answer: 'Pinnacle offers some of the sharpest odds in the market, but they also include a built-in vig (commission), which can affect your profit margins. We remove the vig to give you a clearer understanding of the true odds, allowing you to make more informed decisions when placing bets.', open: false },
    { question: 'Is Sharper-Bets the enough for making betting decision?', answer: 'While Sharper-Bets significantly simplifies the process, making the best betting decisions still requires a bit of your expertise. Our tool handles 90% of the heavy lifting by providing in-depth analysis, team comparisons, and actionable insights. However, we recommend combining our analysis with your knowledge of team form, key metrics, and other factors to ensure the most informed decisions. With Sharper-Bets, you can quickly analyze dozens of matches and pinpoint the one or two most profitable opportunities—saving you time and boosting your success rate!' },
    { question: 'When will the product leave beta and be available for paid subscriptions?', answer: 'The product is currently in beta, and we are actively testing and refining it. We will notify users on the waiting list when we are ready to introduce paid subscriptions.', open: false },
    { question: 'Can I still use the platform after the beta period ends?', answer: 'Absolutely! If you’re part of our waiting list or an early user, you’ll enjoy exclusive access to the platform at special pricing once we move out of beta. Plus, we offer a free version that allows you to analyze up to 5 matches and access 5 real-time odds per day—perfect for getting a taste of what Sharper-Bets can do. Stay ahead of the game and unlock even more features with our premium plans!', open: false },
    { question: 'Can I cancel my subscription after it starts?', answer: 'As we’re in beta, there is no subscription yet. Once we launch paid plans, you will be able to cancel at any time. We’ll provide more details on how subscriptions will work once the product moves beyond beta.', open: false },

  ];

  toggleAnswer(item: any) {
    item.open = !item.open;
  }

  @HostListener('window:scroll', ['$event'])
  onScroll(): void {
    const scrollTop = window.scrollY;
    const windowHeight = window.innerHeight;

    // Handle About Section
    const faqSection = document.getElementById('faq');
    if (faqSection) {
      const aboutOffsetTop = faqSection.offsetTop;
      if (scrollTop + windowHeight > aboutOffsetTop && scrollTop < aboutOffsetTop + faqSection.offsetHeight) {
        this.aboutOpacity = 1; // Fully visible
        this.aboutTransform = 0; // No transform
      } else {
        this.aboutOpacity = 0; // Hidden
        this.aboutTransform = 50; // Slightly moved down
      }
    }
  }


}
