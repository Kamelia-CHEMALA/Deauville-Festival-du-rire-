import json
import unicodedata
from datetime import datetime, date, timedelta


def slug(text):
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


def load_festival():
    with open("data/festival.json", encoding="utf-8") as file:
        return json.load(file)


def find_venue(festival, venue_slug):
    for venue in festival["venues"]:
        if slug(venue["name"]) == venue_slug:
            return venue

    return None


def find_artist(festival, artist_slug):
    for artist in festival["artists"]:
        if slug(artist["name"]) == artist_slug:
            return artist

    return None


def start_of(performance):
    return datetime.fromisoformat(performance["start"])


def end_of(performance):
    start = start_of(performance)
    duration = timedelta(minutes=performance["duration_minutes"])
    return start + duration


def festival_day_of(performance):
    start = start_of(performance)
    return (start - timedelta(hours=6)).date()


def programme(festival, day):
    performances = []

    for performance in festival["performances"]:
        if festival_day_of(performance) == day:
            performances.append(performance)

    return sorted(performances, key=start_of)


def validate_performance(festival, new_performance):
    # Venue must exist
    venue = find_venue(festival, new_performance["venue"])

    if venue is None:
        raise ValueError(f"Unknown venue '{new_performance['venue']}'.")

    # Artist must exist
    artist = find_artist(festival, new_performance["artist"])

    if artist is None:
        raise ValueError(f"Unknown artist '{new_performance['artist']}'.")

    # Duration must be between 1 and 360 minutes
    duration = new_performance["duration_minutes"]

    if duration < 1 or duration > 360:
        raise ValueError("Duration must be between 1 and 360 minutes.")

    new_start = start_of(new_performance)
    new_end = end_of(new_performance)

    # Must belong to a festival day
    festival_days = []

    current_day = date.fromisoformat(festival["first_day"])
    last_day = date.fromisoformat(festival["last_day"])

    while current_day <= last_day:
        festival_days.append(current_day)
        current_day += timedelta(days=1)

    if festival_day_of(new_performance) not in festival_days:
        raise ValueError(
            f"{festival_day_of(new_performance)} is not a day of the festival."
        )

    # Check conflicts with existing performances
    for performance in festival["performances"]:
        existing_start = start_of(performance)
        existing_end = end_of(performance)

        # 30-minute break before/after
        conflict = (
            new_start < existing_end + timedelta(minutes=30)
            and new_end > existing_start - timedelta(minutes=30)
        )

        if conflict:
            # Same venue
            if performance["venue"] == new_performance["venue"]:
                raise ValueError(
                    f"{venue['name']} is busy with "
                    f"{performance['title']} "
                    f"({existing_start:%Y-%m-%d %H:%M}-{existing_end:%H:%M})."
                )

            # Same artist
            artist_slug = new_performance["artist"]

            artist_is_there = (
                performance.get("artist") == artist_slug
                or performance.get("host") == artist_slug
                or artist_slug in performance.get("acts", [])
                or performance.get("teacher") == artist_slug
            )

            if artist_is_there:
                raise ValueError(
                    f"{artist['name']} is on stage in "
                    f"{performance['title']}."
                )


def performance_id(performance):
    start = start_of(performance)

    return (
        f"{performance['venue']}-"
        f"{start:%Y-%m-%d-%H%M}"
    )