"""
Music Controller for JARVIS.

Provides voice-controlled music playback via:
- YouTube Music (preferred - user has premium)
- Spotify (fallback)

Uses URL-based approach (no API keys required).
"""

from __future__ import annotations

import webbrowser
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum

from loguru import logger


class MusicService(str, Enum):
    """Supported music services."""
    YOUTUBE_MUSIC = "youtube_music"
    SPOTIFY = "spotify"


@dataclass
class Playlist:
    """Represents a music playlist."""
    name: str
    youtube_url: Optional[str] = None
    spotify_url: Optional[str] = None
    description: Optional[str] = None
    category: str = "general"  # focus, workout, chill, classical, etc.
    
    def get_url(self, service: MusicService = MusicService.YOUTUBE_MUSIC) -> Optional[str]:
        """Get URL for specified service."""
        if service == MusicService.YOUTUBE_MUSIC:
            return self.youtube_url
        return self.spotify_url


class MusicController:
    """
    Voice-controlled music player.
    
    Opens playlists in browser for YouTube Music or Spotify.
    Integrates with Pomodoro for focus music.
    Supports YouTube Music Premium personal library access.
    
    Usage:
        controller = MusicController()
        controller.play("focus")
        controller.play_search("hindi songs")
        controller.play_liked_songs()
        controller.play_my_mix()
    """
    
    # YouTube Music Personal Library URLs (requires Premium/login)
    YOUTUBE_MUSIC_PERSONAL = {
        "liked_songs": "https://music.youtube.com/playlist?list=LM",
        "library": "https://music.youtube.com/library",
        "history": "https://music.youtube.com/history",
        "my_mix": "https://music.youtube.com/watch?list=RDAMVM",
        "discover_mix": "https://music.youtube.com/playlist?list=RDTMAK5uy_kset8DmRd8JELhIvnFfgzTmTKJv8c",
        "new_releases": "https://music.youtube.com/new_releases",
        "charts": "https://music.youtube.com/charts",
        "moods": "https://music.youtube.com/moods_and_genres",
    }
    
    # Pre-configured playlists for students
    DEFAULT_PLAYLISTS = {
        # Focus/Study playlists
        "focus": Playlist(
            name="Focus Music",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_kmPRjHDECIcuVwnKsx2Ng7fyNgFKWNJFs",
            spotify_url="https://open.spotify.com/playlist/0vvXsWCC9xrXsKd4FyS8kM",
            description="Deep focus music for studying",
            category="focus"
        ),
        "lofi": Playlist(
            name="Lo-Fi Beats",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_n9Fbdw7e6ap-98fLY_GynOLXhJRoWIKj8",
            spotify_url="https://open.spotify.com/playlist/0vvXsWCC9xrXsKd4FyS8kM",
            description="Lo-fi hip hop beats to study/relax to",
            category="focus"
        ),
        "study": Playlist(
            name="Study Music",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_kzInpZMIlBXPOZvSJHFMvWbLlLueVNFN4",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX8NTLI2TtZa6",
            description="Calm music for studying",
            category="focus"
        ),
        "classical": Playlist(
            name="Classical Focus",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_nMGwlqYAKbnGmVUXxN-ZlDKL0Yl9XZlEo",
            spotify_url="https://open.spotify.com/playlist/1h0CEZCm6IbFTbxThn6Xcs",
            description="Classical music for concentration",
            category="classical"
        ),
        "ambient": Playlist(
            name="Ambient Study",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_mfut9V_o1n9nVG_m5yZ3ztCif29AHUffI",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DWZd79rJ6a7lp",
            description="Ambient sounds for deep work",
            category="focus"
        ),
        
        # Workout playlists
        "gym": Playlist(
            name="Gym Workout",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_k6D4lQTjlrKvnoxxBphEwHq4Rw-6v0Kyc",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX76Wlfdnj7AP",
            description="High energy workout music",
            category="workout"
        ),
        "workout": Playlist(
            name="Workout Mix",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_k6D4lQTjlrKvnoxxBphEwHq4Rw-6v0Kyc",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX70RN3TfWWJh",
            description="Workout motivation",
            category="workout"
        ),
        
        # Hindi/Bollywood
        "hindi": Playlist(
            name="Hindi Hits",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_nkalSYoLQGhRrBd6LjIhOXH8B8UrLCbGk",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX0XUfTFmNBRM",
            description="Latest Hindi songs",
            category="hindi"
        ),
        "bollywood": Playlist(
            name="Bollywood Hits",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_nkalSYoLQGhRrBd6LjIhOXH8B8UrLCbGk",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX0XUfTFmNBRM",
            description="Bollywood music",
            category="hindi"
        ),
        
        # Chill/Relax
        "chill": Playlist(
            name="Chill Vibes",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_n9Fbdw7e6ap-98fLY_GynOLXhJRoWIKj8",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX4WYpdgoIcn6",
            description="Chill and relaxing music",
            category="chill"
        ),
        "relax": Playlist(
            name="Relaxation",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_mfut9V_o1n9nVG_m5yZ3ztCif29AHUffI",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DWU0ScTcjJBdj",
            description="Relaxing music",
            category="chill"
        ),
        
        # Nature/ASMR
        "nature": Playlist(
            name="Nature Sounds",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_mDoRMCYvPaRiLqFQrDrUF6ZPMY-cagWVU",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX4PP3DA4J0N8",
            description="Nature sounds for focus",
            category="nature"
        ),
        "rain": Playlist(
            name="Rain Sounds",
            youtube_url="https://www.youtube.com/watch?v=mPZkdNFkNps",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX8ymr6UES7vc",
            description="Rain sounds for concentration",
            category="nature"
        ),
        
        # Coding specific
        "coding": Playlist(
            name="Coding Music",
            youtube_url="https://music.youtube.com/playlist?list=RDCLAK5uy_kmPRjHDECIcuVwnKsx2Ng7fyNgFKWNJFs",
            spotify_url="https://open.spotify.com/playlist/37i9dQZF1DX5trt9i14X7j",
            description="Music for coding sessions",
            category="focus"
        ),
        
        # Personal Library shortcuts (YouTube Music Premium)
        "liked": Playlist(
            name="My Liked Songs",
            youtube_url="https://music.youtube.com/playlist?list=LM",
            description="Your liked songs on YouTube Music",
            category="personal"
        ),
        "my_mix": Playlist(
            name="My Mix",
            youtube_url="https://music.youtube.com/watch?list=RDAMVM",
            description="Your personalized mix",
            category="personal"
        ),
        "discover": Playlist(
            name="Discover Mix",
            youtube_url="https://music.youtube.com/playlist?list=RDTMAK5uy_kset8DmRd8JELhIvnFfgzTmTKJv8c",
            description="Discover new music",
            category="personal"
        ),
    }
    
    def __init__(
        self,
        preferred_service: MusicService = MusicService.YOUTUBE_MUSIC,
        custom_playlists: Optional[Dict[str, Playlist]] = None,
    ):
        """
        Initialize music controller.
        
        Args:
            preferred_service: Preferred music service (YouTube Music or Spotify)
            custom_playlists: Additional custom playlists
        """
        self.preferred_service = preferred_service
        self.playlists = dict(self.DEFAULT_PLAYLISTS)
        
        if custom_playlists:
            self.playlists.update(custom_playlists)
        
        self.current_playlist: Optional[str] = None
        self._is_playing = False
    
    def play(self, playlist_name: str) -> str:
        """
        Play a playlist by name.
        
        Args:
            playlist_name: Name of playlist to play
            
        Returns:
            Status message
        """
        # Normalize name
        name_lower = playlist_name.lower().strip()
        
        # Find matching playlist
        playlist = None
        for key, pl in self.playlists.items():
            if key == name_lower or name_lower in key or name_lower in pl.name.lower():
                playlist = pl
                break
        
        if not playlist:
            # Try category match
            for key, pl in self.playlists.items():
                if name_lower in pl.category:
                    playlist = pl
                    break
        
        if not playlist:
            return f"Playlist '{playlist_name}' not found. Try: focus, lofi, hindi, gym, classical, coding"
        
        # Get URL for preferred service
        url = playlist.get_url(self.preferred_service)
        
        if not url:
            # Fallback to other service
            other_service = (MusicService.SPOTIFY if self.preferred_service == MusicService.YOUTUBE_MUSIC 
                           else MusicService.YOUTUBE_MUSIC)
            url = playlist.get_url(other_service)
        
        if not url:
            return f"No URL available for playlist '{playlist.name}'"
        
        # Open in browser
        try:
            webbrowser.open(url)
            self.current_playlist = playlist.name
            self._is_playing = True
            
            service_name = "YouTube Music" if "youtube" in url else "Spotify"
            logger.info(f"Playing {playlist.name} on {service_name}")
            return f"🎵 Playing {playlist.name} on {service_name}"
            
        except Exception as e:
            logger.error(f"Failed to open music: {e}")
            return f"Failed to open music player: {str(e)}"
    
    def play_search(self, query: str) -> str:
        """
        Search and play music by query.
        
        Args:
            query: Search query (song name, artist, genre)
            
        Returns:
            Status message
        """
        # Build search URL
        if self.preferred_service == MusicService.YOUTUBE_MUSIC:
            search_url = f"https://music.youtube.com/search?q={query.replace(' ', '+')}"
        else:
            search_url = f"https://open.spotify.com/search/{query.replace(' ', '%20')}"
        
        try:
            webbrowser.open(search_url)
            service_name = "YouTube Music" if self.preferred_service == MusicService.YOUTUBE_MUSIC else "Spotify"
            logger.info(f"Searching for '{query}' on {service_name}")
            return f"🔍 Searching for '{query}' on {service_name}"
            
        except Exception as e:
            logger.error(f"Failed to search music: {e}")
            return f"Failed to search: {str(e)}"
    
    def play_focus_music(self) -> str:
        """Play focus music (shortcut for Pomodoro integration)."""
        return self.play("focus")
    
    def play_workout_music(self) -> str:
        """Play workout music."""
        return self.play("gym")
    
    # =========================================================================
    # YouTube Music Personal Library Methods (Premium)
    # =========================================================================
    
    def play_liked_songs(self) -> str:
        """Play user's liked songs on YouTube Music."""
        url = self.YOUTUBE_MUSIC_PERSONAL["liked_songs"]
        return self._open_personal_url(url, "Liked Songs")
    
    def play_library(self) -> str:
        """Open YouTube Music library."""
        url = self.YOUTUBE_MUSIC_PERSONAL["library"]
        return self._open_personal_url(url, "Your Library")
    
    def play_history(self) -> str:
        """Play recently played on YouTube Music."""
        url = self.YOUTUBE_MUSIC_PERSONAL["history"]
        return self._open_personal_url(url, "Recently Played")
    
    def play_my_mix(self) -> str:
        """Play personalized mix on YouTube Music."""
        url = self.YOUTUBE_MUSIC_PERSONAL["my_mix"]
        return self._open_personal_url(url, "Your Mix")
    
    def play_discover_mix(self) -> str:
        """Play discover mix on YouTube Music."""
        url = self.YOUTUBE_MUSIC_PERSONAL["discover_mix"]
        return self._open_personal_url(url, "Discover Mix")
    
    def play_new_releases(self) -> str:
        """Open new releases on YouTube Music."""
        url = self.YOUTUBE_MUSIC_PERSONAL["new_releases"]
        return self._open_personal_url(url, "New Releases")
    
    def play_charts(self) -> str:
        """Open music charts on YouTube Music."""
        url = self.YOUTUBE_MUSIC_PERSONAL["charts"]
        return self._open_personal_url(url, "Charts")
    
    def browse_moods(self) -> str:
        """Browse moods and genres on YouTube Music."""
        url = self.YOUTUBE_MUSIC_PERSONAL["moods"]
        return self._open_personal_url(url, "Moods & Genres")
    
    def _open_personal_url(self, url: str, name: str) -> str:
        """Open a personal YouTube Music URL."""
        try:
            webbrowser.open(url)
            self.current_playlist = name
            self._is_playing = True
            logger.info(f"Opening {name} on YouTube Music")
            return f"🎵 Opening {name} on YouTube Music"
        except Exception as e:
            logger.error(f"Failed to open {name}: {e}")
            return f"Failed to open {name}: {str(e)}"
    
    def search_youtube_music(self, query: str) -> str:
        """
        Search on YouTube Music specifically.
        
        Args:
            query: Search query
            
        Returns:
            Status message
        """
        from urllib.parse import quote_plus
        search_url = f"https://music.youtube.com/search?q={quote_plus(query)}"
        
        try:
            webbrowser.open(search_url)
            logger.info(f"Searching YouTube Music for: {query}")
            return f"🔍 Searching YouTube Music for '{query}'"
        except Exception as e:
            logger.error(f"Failed to search: {e}")
            return f"Failed to search: {str(e)}"
    
    def get_playlists(self, category: Optional[str] = None) -> List[Playlist]:
        """
        Get available playlists.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of playlists
        """
        if category:
            return [p for p in self.playlists.values() if p.category == category]
        return list(self.playlists.values())
    
    def list_playlists(self) -> str:
        """Get formatted list of available playlists."""
        categories = {}
        for name, playlist in self.playlists.items():
            cat = playlist.category
            if cat not in categories:
                categories[cat] = []
            categories[cat].append(name)
        
        lines = ["🎵 Available Playlists:"]
        for cat, names in sorted(categories.items()):
            lines.append(f"\n{cat.title()}:")
            for name in names:
                lines.append(f"  • {name}")
        
        return "\n".join(lines)
    
    def add_playlist(
        self,
        name: str,
        youtube_url: Optional[str] = None,
        spotify_url: Optional[str] = None,
        category: str = "custom",
    ) -> str:
        """
        Add a custom playlist.
        
        Args:
            name: Playlist name
            youtube_url: YouTube Music URL
            spotify_url: Spotify URL
            category: Playlist category
            
        Returns:
            Status message
        """
        key = name.lower().replace(" ", "_")
        self.playlists[key] = Playlist(
            name=name,
            youtube_url=youtube_url,
            spotify_url=spotify_url,
            category=category,
        )
        return f"Added playlist '{name}'"
    
    def get_current(self) -> str:
        """Get currently playing playlist info."""
        if self.current_playlist:
            return f"🎵 Currently playing: {self.current_playlist}"
        return "No music currently playing through JARVIS"
    
    @property
    def is_playing(self) -> bool:
        """Check if music was started (note: can't track actual playback state)."""
        return self._is_playing
