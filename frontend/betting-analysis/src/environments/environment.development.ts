import {firebase} from "firebaseui-angular";
import * as firebaseui from 'firebaseui';


export const environment = {
  production:false,
  apiUrl: 'http://localhost:9000',
  firebaseConfig:{
  apiKey: "AIzaSyAghUa10H_pBWXPunsbH1g7JWSWxSyXIf4",
  authDomain: "sharper-bets.firebaseapp.com",
  projectId: "sharper-bets",
  storageBucket: "sharper-bets.firebasestorage.app",
  messagingSenderId: "762149786749",
  appId: "1:762149786749:web:b65d11d226e8306cb14d14",
  measurementId: "G-D5NNYQW1PC"
},
  firebaseUiAuthConfig: {
  signInOptions: [
    firebase.auth.GoogleAuthProvider.PROVIDER_ID,
  ],
   signInSuccessUrl: '/', // Redirect to home page after successful login
  callbacks: {
    signInSuccessWithAuthResult: (authResult: any, redirectUrl: any) => {
      console.log('User signed in successfully:', authResult);
      window.location.href = '/';
      return false; // Prevent FirebaseUI from redirecting automatically
    },
  },
  credentialHelper: firebaseui.auth.CredentialHelper.NONE,
  signInFlow: 'popup', // You can also use 'redirect'
  tosUrl: '/terms-of-service', // Replace with your TOS URL
  privacyPolicyUrl: '/privacy-policy', // Replace with your privacy policy URL
}
 };
