export interface Outcome {
  name: string;
  price: number;
  no_vig_price?: number; // Optional, as not all outcomes have this field
}

export interface Market {
  outcomes: Outcome[];
}

export interface Bookmaker {
  name: string; // Add name for the bookmaker
  markets: Market[];
}

export interface Match {
  id?:string;
  home_team: string;
  away_team: string;
  commence_time: string;
  bookmakers: Bookmaker[]; // Change to an array of Bookmakers
}

export interface OddsData {
  bookmaker_data: Match[]; // This remains unchanged
}
