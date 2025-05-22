export interface Player {
  name: string;
  jersey_number: number;
  market_value: number;
}

export interface ComparisonItem {
  position: string;
  home_player: Player | null;
  away_player: Player | null;
  result?: string; // Optional if not always provided
}

export interface MatchComparison {
  home_team: string;
  away_team: string;
  comparison: ComparisonItem[];
}
