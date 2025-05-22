import { Routes } from '@angular/router';
import {HomeComponent} from "./home/home.component";
import {ProAnalysisComponent} from "./pro-analysis/pro-analysis.component";
import {RealtimeoddsComponent} from "./realtimeodds/realtimeodds.component";
import {AboutUsComponent} from "./about-us/about-us.component";

import {AuthGuard, redirectUnauthorizedTo} from '@angular/fire/auth-guard';
import {SignupComponent} from "./signup/signup.component";
import {SigninComponent} from "./signin/signin.component";


const redirectUnauthorizedToLogin = () => redirectUnauthorizedTo(['login']);

export const routes: Routes = [
   { path: '', component: HomeComponent },
  { path: 'login', component: SignupComponent },
   { path: 'pro-analysis/:home_team/:away_team', component: ProAnalysisComponent,canActivate: [AuthGuard],
   data: {authGuardPipe: redirectUnauthorizedToLogin} },
   { path: 'pro-analysis', component: ProAnalysisComponent, canActivate: [AuthGuard],
   data: {authGuardPipe: redirectUnauthorizedToLogin}},
   { path: 'real-time-odds', component: RealtimeoddsComponent, canActivate: [AuthGuard],
   data: {authGuardPipe: redirectUnauthorizedToLogin} },
   {path:'about-us', component: AboutUsComponent},
  {path:'sign-in', component: SigninComponent}
];
