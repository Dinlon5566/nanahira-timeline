export type Lang = 'ja' | 'en' | 'zh';

export type HerRatio = 'all' | 'some' | 'none';
export type HerRole = 'lead' | 'duet' | 'chorus' | 'voice' | 'composer' | 'lyricist';
export type DisplayRole = 'lead' | 'guest' | 'tiein';

export interface Cover {
  url: string;
  source: 'itunes' | 'spotify' | 'manual' | 'local';
  size?: number;
}

export interface Album {
  id: string;
  title_jp: string;
  title_romaji: string | null;
  title_en: string | null;
  release_date: string;           // YYYY-MM-DD
  catalog: string;
  event: string | null;           // C93 / M3-2023春
  format: string | null;          // CD / 2CD / Digital
  publisher: string | null;
  tracks_count: number;
  her_tracks_count: number;
  her_ratio: HerRatio;
  roles: string[];
  display_role: DisplayRole;
  cover: Cover | null;
  sources: {
    vgmdb?: string;
    spotify_album_id?: string;
    apple_album_id?: string;
  };
  external_links?: ExternalLinks;
}

export interface ExternalLinks {
  youtube?: string;
  spotify?: string;
  apple_music?: string;
  niconico?: string;
  soundcloud?: string;
  bandcamp?: string;
  official?: string;
}

export interface Track {
  id: string;
  album_id: string;
  disc: number;
  track_no: number;
  title: string;
  duration: string | null;
  her: boolean;
  her_role: HerRole | null;
  vocal_credits: string[];
  cover: Cover | null;
}

export interface MilestoneEvent {
  type: 'milestone';
  date: string;                   // YYYY-MM-DD
  label: Record<Lang, string>;
  category?: 'release' | 'live' | 'breakthrough' | 'anniversary' | 'media';
  highlight?: boolean;
  link?: string;
}

export interface ReleaseEvent {
  type: 'release';
  date: string;
  album_id: string;
}

export type TimelineEvent = MilestoneEvent | ReleaseEvent;

export interface Year {
  year: number;
  release_count: number;
  milestone_count: number;
  events: TimelineEvent[];        // sorted by date desc
}

export interface Timeline {
  years: Year[];                  // sorted desc (newest first)
  total_releases: number;
  total_milestones: number;
}

export interface Alias {
  name_jp: string;
  name_en?: string;
  type: 'stage_name' | 'unit' | 'vtuber' | 'synth_voice' | 'character';
  since?: string;
  status?: 'active' | 'past' | 'ongoing';
  affiliation?: string;
  description: Record<Lang, string>;
  links?: { youtube?: string; twitter?: string; website?: string };
}
