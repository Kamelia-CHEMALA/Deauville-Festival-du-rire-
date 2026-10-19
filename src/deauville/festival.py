from __future__ import annotations

import json
import unicodedata
from abc import ABC, abstractmethod
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Any


class FestivalError(Exception):
    """Base exception for festival business-rule failures."""

    pass


class NotFoundError(FestivalError):
    """Raised when a requested festival resource does not exist."""

    pass


class ConflictError(FestivalError):
    """Raised when a requested operation conflicts with festival rules."""

    pass


class InvalidError(FestivalError):
    """Raised when an input violates a validation rule."""

    pass


class Performance(ABC):
    """Abstract base class for all festival performances."""

    def __init__(
        self,
        title: str,
        venue: str,
        start: str,
        duration_minutes: int,
        description: str = "",
    ) -> None:
        self.title = title
        self.venue = venue
        self.start = datetime.fromisoformat(start)
        self.duration_minutes = duration_minutes
        self.description = description

    def end(self) -> datetime:
        return self.start + timedelta(minutes=self.duration_minutes)

    def festival_day(self) -> date:
        """Return the festival date, with the day changing at 06:00."""
        return (self.start - timedelta(hours=6)).date()

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "title": self.title,
            "venue": self.venue,
            "start": self.start.strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": self.duration_minutes,
            "description": self.description,
        }

    @abstractmethod
    def role_of(self, artist_slug: str) -> str | None:
        """Return the role of an artist in this performance, if any."""
        pass

    def view(self, festival: Festival) -> dict[str, Any]:
        """Build the API representation of this performance."""
        venue = find_venue(festival, self.venue)
        return {
            "id": performance_id(self),
            "kind": self.kind,
            "title": self.title,
            "venue": self.venue,
            "venue_name": venue["name"],
            "start": self.start.strftime("%Y-%m-%dT%H:%M"),
            "end": self.end().strftime("%Y-%m-%dT%H:%M"),
            "duration_minutes": self.duration_minutes,
            "festival_day": self.festival_day().isoformat(),
            "description": self.description,
            "summary": self.summary(festival),
            "capacity": venue["capacity"],
            "artists": [
                {
                    "slug": artist_slug,
                    "name": find_artist(festival, artist_slug)["name"],
                }
                for artist_slug in self.artists()
            ],
        }

    @abstractmethod
    def artists(self) -> list[str]:
        pass

    @abstractmethod
    def summary(self, festival: Festival) -> str:
        pass


class SoloShow(Performance):
    """A solo performance featuring one artist."""

    kind = "solo"

    def __init__(
        self,
        title: str,
        venue: str,
        start: str,
        duration_minutes: int,
        artist: str,
        min_age: int = 0,
        description: str = "",
    ) -> None:
        super().__init__(title, venue, start, duration_minutes, description)
        if min_age < 0 or min_age > 18:
            raise InvalidError("Minimum age must be between 0 and 18.")
        self.artist = artist
        self.min_age = min_age

    def artists(self) -> list[str]:
        return [self.artist]

    def summary(self, festival: Festival) -> str:
        artist = find_artist(festival, self.artist)
        return artist["name"]

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["artist"] = self.artist
        data["min_age"] = self.min_age
        return data

    def role_of(self, artist_slug: str) -> str | None:
        """Return the role of an artist in this performance, if any."""
        if artist_slug == self.artist:
            return "solo"
        return None

    def view(self, festival: Festival) -> dict[str, Any]:
        """Build the API representation of this performance."""
        data = super().view(festival)
        data["artist"] = self.artist
        data["min_age"] = self.min_age
        return data


class Lineup(Performance):
    """A hosted performance featuring multiple acts."""

    kind = "lineup"

    def __init__(
        self,
        title: str,
        venue: str,
        start: str,
        duration_minutes: int,
        host: str,
        acts: list[str],
        description: str = "",
    ) -> None:
        super().__init__(title, venue, start, duration_minutes, description)
        if len(acts) < 2:
            raise InvalidError("A lineup must have at least 2 acts.")
        if len(acts) != len(set(acts)):
            raise InvalidError("Each act must appear only once.")
        if host in acts:
            raise InvalidError("The host cannot also be an act.")
        minimum_duration = len(acts) * 10 + (len(acts) - 1) * 3
        if duration_minutes < minimum_duration:
            raise InvalidError(
                f"A lineup with {len(acts)} acts needs at least "
                f"{minimum_duration} minutes."
            )
        self.host = host
        self._acts = tuple(acts)

    @property
    def acts(self) -> list[str]:
        return list(self._acts)

    def artists(self) -> list[str]:
        return [self.host] + self.acts

    def summary(self, festival: Festival) -> str:
        host = find_artist(festival, self.host)
        acts = [find_artist(festival, artist)["name"] for artist in self.acts]
        return f"hosted by {host['name']}, with " + ", ".join(acts)

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["host"] = self.host
        data["acts"] = self.acts
        return data

    def role_of(self, artist_slug: str) -> str | None:
        """Return the role of an artist in this performance, if any."""
        if artist_slug == self.host:
            return "host"
        if artist_slug in self.acts:
            return "act"
        return None

    def view(self, festival: Festival) -> dict[str, Any]:
        """Build the API representation of this performance."""
        data = super().view(festival)
        data["host"] = self.host
        data["acts"] = self.acts
        return data


class Workshop(Performance):
    """A workshop with limited participant registration."""

    kind = "workshop"

    def __init__(
        self,
        title: str,
        venue: str,
        start: str,
        duration_minutes: int,
        teacher: str,
        max_participants: int,
        participants: list[str] | None = None,
        description: str = "",
    ) -> None:
        super().__init__(title, venue, start, duration_minutes, description)
        if max_participants < 1:
            raise InvalidError("A workshop must have at least 1 place.")
        self.teacher = teacher
        self.max_participants = max_participants
        self._participants = tuple(participants or [])

    @property
    def participants(self) -> list[str]:
        return list(self._participants)

    def artists(self) -> list[str]:
        return [self.teacher]

    def capacity(self, festival: Festival) -> int:
        venue = find_venue(festival, self.venue)
        return min(self.max_participants, venue["capacity"])

    def places_left(self, festival: Festival) -> int:
        return self.capacity(festival) - len(self.participants)

    def register_participant(self, festival: Festival, name: str) -> None:
        """Register a unique participant when places remain."""
        name = name.strip()
        if not name:
            raise InvalidError("Participant name cannot be empty.")
        if any(
            participant.casefold() == name.casefold()
            for participant in self._participants
        ):
            raise ConflictError("Participant already registered.")
        if self.places_left(festival) <= 0:
            raise ConflictError("Workshop is full.")
        self._participants = self._participants + (name,)

    def summary(self, festival: Festival) -> str:
        teacher = find_artist(festival, self.teacher)
        capacity = self.capacity(festival)
        return (
            f"with {teacher['name']}, {len(self.participants)}/{capacity} places taken"
        )

    def to_dict(self) -> dict[str, Any]:
        data = super().to_dict()
        data["teacher"] = self.teacher
        data["max_participants"] = self.max_participants
        data["participants"] = self.participants
        return data

    def role_of(self, artist_slug: str) -> str | None:
        """Return the role of an artist in this performance, if any."""
        if artist_slug == self.teacher:
            return "teacher"
        return None

    def view(self, festival: Festival) -> dict[str, Any]:
        """Build the API representation of this performance."""
        data = super().view(festival)
        data["teacher"] = self.teacher
        data["max_participants"] = self.max_participants
        data["participants"] = self.participants
        data["places_left"] = self.places_left(festival)
        data["capacity"] = self.capacity(festival)
        return data


def slug(text: str) -> str:
    """Create a URL-safe identifier from a name."""
    text = unicodedata.normalize("NFKD", text)
    text = text.encode("ascii", "ignore").decode("ascii")
    text = text.lower()
    result = ""
    for character in text:
        if character.isalnum():
            result += character
        elif character == " " and result and not result.endswith("-"):
            result += "-"
    return result.strip("-")


class Festival(dict):
    """Festival data and controlled performance operations."""

    def __init__(self, data: dict[str, Any]) -> None:
        super().__init__(data)
        self._performances = tuple(data["performances"])

    def __getitem__(self, key: str) -> Any:
        if key == "performances":
            return list(self._performances)
        return super().__getitem__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        if key == "performances":
            raise InvalidError("Use Festival methods to modify performances.")
        super().__setitem__(key, value)

    def add_performance(self, performance: Performance) -> None:
        validate_performance(self, performance)
        self._performances = self._performances + (performance,)

    def cancel_performance(self, performance_id_value: str) -> None:
        for performance in self._performances:
            if performance_id(performance) == performance_id_value:
                self._performances = tuple(
                    p for p in self._performances if p is not performance
                )
                return
        raise NotFoundError(f"Performance '{performance_id_value}' not found.")

    def move_performance(
        self, performance_id_value: str, new_performance: Performance
    ) -> None:
        """Validate a replacement before changing the stored programme."""
        old_performance = None
        for performance in self._performances:
            if performance_id(performance) == performance_id_value:
                old_performance = performance
                break
        if old_performance is None:
            raise NotFoundError(f"Performance '{performance_id_value}' not found.")
        # On prépare une liste sans l'ancien spectacle
        remaining = tuple(p for p in self._performances if p is not old_performance)
        # On vérifie le nouvel horaire sans modifier le programme
        original_performances = self._performances
        try:
            self._performances = remaining
            validate_performance(self, new_performance)
        finally:
            self._performances = original_performances
        # On remplace uniquement si la validation a réussi
        self._performances = remaining + (new_performance,)

    def add_artist(
        self, name: str, bio: str = "", photo_url: str = ""
    ) -> dict[str, Any]:
        name = name.strip()
        if not name:
            raise InvalidError("Artist name cannot be empty.")
        if any(slug(artist["name"]) == slug(name) for artist in self["artists"]):
            raise ConflictError("Artist already exists.")
        artist = {"name": name, "bio": bio, "photo_url": photo_url}
        self["artists"].append(artist)
        return artist


def load_festival(path: str | Path = "data/festival.json") -> Festival:
    """Load JSON data and instantiate the appropriate performance classes."""
    with open(path, encoding="utf-8") as file:
        festival = json.load(file)
    classes = {"solo": SoloShow, "lineup": Lineup, "workshop": Workshop}
    performances = []
    for data in festival["performances"]:
        performance_class = classes[data["kind"]]
        performance_data = data.copy()
        del performance_data["kind"]
        performance = performance_class(**performance_data)
        performances.append(performance)
    festival["performances"] = performances
    return Festival(festival)


def find_venue(festival: Festival, venue_slug: str) -> dict[str, Any] | None:
    for venue in festival["venues"]:
        if slug(venue["name"]) == venue_slug:
            return venue
    return None


def find_artist(festival: Festival, artist_slug: str) -> dict[str, Any] | None:
    for artist in festival["artists"]:
        if slug(artist["name"]) == artist_slug:
            return artist
    return None


def start_of(performance: Performance) -> datetime:
    return performance.start


def end_of(performance: Performance) -> datetime:
    return performance.end()


def festival_day_of(performance: Performance) -> date:
    return performance.festival_day()


def programme(festival: Festival, day: date) -> list[Performance]:
    """Return performances for one festival day in chronological order."""
    performances = []
    for performance in festival["performances"]:
        if festival_day_of(performance) == day:
            performances.append(performance)
    return sorted(performances, key=start_of)


def validate_performance(festival: Festival, new_performance: Performance) -> None:
    # Venue must exist
    """Enforce venue, artist, duration, date, and scheduling rules."""
    venue = find_venue(festival, new_performance.venue)
    if venue is None:
        raise NotFoundError(f"Unknown venue '{new_performance.venue}'.")
    # All artists must exist
    for artist_slug in new_performance.artists():
        artist = find_artist(festival, artist_slug)
        if artist is None:
            raise NotFoundError(f"Unknown artist '{artist_slug}'.")
    # Duration must be between 1 and 360 minutes
    duration = new_performance.duration_minutes
    if duration < 1 or duration > 360:
        raise InvalidError("Duration must be between 1 and 360 minutes.")
    new_start = start_of(new_performance)
    new_end = end_of(new_performance)
    # Must belong to a festival day
    first_day = date.fromisoformat(festival["first_day"])
    last_day = date.fromisoformat(festival["last_day"])
    new_day = festival_day_of(new_performance)
    if new_day < first_day or new_day > last_day:
        raise ConflictError(f"{new_day} is not a day of the festival.")
    # Check conflicts
    for performance in festival["performances"]:
        existing_start = start_of(performance)
        existing_end = end_of(performance)
        conflict = new_start < existing_end + timedelta(
            minutes=30
        ) and new_end > existing_start - timedelta(minutes=30)
        if not conflict:
            continue
        # Same venue
        if performance.venue == new_performance.venue:
            raise ConflictError(
                f"{venue['name']} is busy with "
                f"{performance.title} "
                f"({existing_start:%Y-%m-%d %H:%M}-{existing_end:%H:%M})."
            )
        # Same artist
        common_artists = set(new_performance.artists()) & set(performance.artists())
        if common_artists:
            artist_slug = next(iter(common_artists))
            artist = find_artist(festival, artist_slug)
            raise ConflictError(f"{artist['name']} is on stage in {performance.title}.")


def performance_id(performance: Performance) -> str:
    """Build the stable identifier from venue and start time."""
    start = start_of(performance)
    return f"{performance.venue}-{start:%Y-%m-%d-%H%M}"
