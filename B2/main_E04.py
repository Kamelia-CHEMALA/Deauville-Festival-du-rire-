import json
import sys
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

def programme(festival, day):
    performances = []

    for performance in festival["performances"]:
        if festival_day_of(performance) == day:
            performances.append(performance)

    return sorted(performances, key=start_of)


def print_summary(festival):
    print(festival["name"])
    print(f"From {festival['first_day']} to {festival['last_day']}")
    print(
        f"{len(festival['venues'])} venues, "
        f"{len(festival['artists'])} artists, "
        f"{len(festival['performances'])} performances"
    )


def print_venues(festival):
    total_seats = 0

    for venue in festival["venues"]:
        venue_slug = slug(venue["name"])
        print(f"{venue_slug}: {venue['name']}, {venue['capacity']} seats")
        total_seats += venue["capacity"]

    print(f"Total: {total_seats} seats")


def print_programme(festival, day):
    print(f"Programme for {day:%A %d %B}:")

    for performance in programme(festival, day):
        venue = find_venue(festival, performance["venue"])

        start = start_of(performance)
        end = end_of(performance)

        print(
            f"{start:%H:%M}-{end:%H:%M} | "
            f"{venue['name']} | "
            f"{performance['title']} ({performance['kind']})"
        )

def print_artist(festival, artist_slug):
    artist = find_artist(festival, artist_slug)

    if artist is None:
        print(f"No artist '{artist_slug}'.")
        return

    print(artist["name"])

    for performance in festival["performances"]:
        role = None

        if performance.get("artist") == artist_slug:
            role = "solo"

        elif performance.get("host") == artist_slug:
            role = "host"

        elif artist_slug in performance.get("acts", []):
            role = "act"

        elif performance.get("teacher") == artist_slug:
            role = "teacher"

        if role is not None:
            venue = find_venue(festival, performance["venue"])
            start = start_of(performance)
            end = end_of(performance)
            festival_day = festival_day_of(performance)

            print(
                f"{festival_day:%a %d} {start:%H:%M}-{end:%H:%M} | "
                f"{venue['name']} | "
                f"{performance['title']} ({role})"
            )


def print_now(festival, moment):
    on_stage = []
    upcoming = []

    for performance in festival["performances"]:
        start = start_of(performance)
        end = end_of(performance)

        if start <= moment < end:
            on_stage.append(performance)

        elif start > moment:
            upcoming.append(performance)

    upcoming = sorted(upcoming, key=start_of)[:3]

    print(f"On stage at {moment:%Y-%m-%d %H:%M}:")

    for performance in on_stage:
        venue = find_venue(festival, performance["venue"])
        end = end_of(performance)

        print(
            f"- {performance['title']} at "
            f"{venue['name']}, until {end:%H:%M}"
        )

    print("Up next:")

    for performance in upcoming:
        venue = find_venue(festival, performance["venue"])
        start = start_of(performance)
        end = end_of(performance)

        print(
            f"- {start:%H:%M}-{end:%H:%M} | "
            f"{venue['name']} | "
            f"{performance['title']} ({performance['kind']})"
        )

festival = load_festival()

def start_of(performance):
    return datetime.fromisoformat(performance["start"])


def end_of(performance):
    start = start_of(performance)
    duration = timedelta(minutes=performance["duration_minutes"])
    return start + duration


def festival_day_of(performance):
    start = start_of(performance)
    return (start - timedelta(hours=6)).date()


if len(sys.argv) == 1:
    print_summary(festival)

elif sys.argv[1] == "venues":
    print_venues(festival)

elif sys.argv[1] == "programme" and len(sys.argv) == 3:
    day = date.fromisoformat(sys.argv[2])
    print_programme(festival, day)

elif sys.argv[1] == "artist" and len(sys.argv) == 3:
    print_artist(festival, sys.argv[2])

elif sys.argv[1] == "now" and len(sys.argv) == 3:
    moment = datetime.fromisoformat(sys.argv[2])
    print_now(festival, moment)

else:
    print("Usage:")
    print("  uv run main.py")
    print("  uv run main.py venues")
    print("  uv run main.py programme YYYY-MM-DD")
    print("  uv run main.py artist ARTIST-SLUG")
    print("  uv run main.py now YYYY-MM-DDTHH:MM")
    
