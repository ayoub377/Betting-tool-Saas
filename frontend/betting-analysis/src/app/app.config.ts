import {ApplicationConfig, importProvidersFrom} from '@angular/core';
import { provideRouter } from '@angular/router';

import { routes } from './app.routes';
import {HTTP_INTERCEPTORS, provideHttpClient} from "@angular/common/http";
import { provideAnimationsAsync } from '@angular/platform-browser/animations/async';
import {initializeApp, provideFirebaseApp} from "@angular/fire/app";

import {getAuth, provideAuth} from "@angular/fire/auth";
import {environment} from "../environments/environment";
import {getFirestore, provideFirestore} from "@angular/fire/firestore";
import {FIREBASE_OPTIONS} from "@angular/fire/compat";
import {FirebaseUIModule} from "firebaseui-angular";
import {HttpErrorInterceptor} from "./interceptors/http-error.interceptor";
import {getAnalytics, provideAnalytics} from "@angular/fire/analytics";

export const appConfig: ApplicationConfig = {
  providers: [
    { provide: FIREBASE_OPTIONS, useValue: environment.firebaseConfig },
    { provide: HTTP_INTERCEPTORS, useClass: HttpErrorInterceptor, multi: true },
    provideFirebaseApp(() => initializeApp(environment.firebaseConfig),),
    provideAuth(() => getAuth()),
    provideFirestore(() => getFirestore()),
    provideAnalytics(() => getAnalytics()),
    importProvidersFrom(
       FirebaseUIModule.forRoot(environment.firebaseUiAuthConfig),
    ),
    provideRouter(routes),
    provideHttpClient(),
    provideAnimationsAsync('noop'),
  ]
};
