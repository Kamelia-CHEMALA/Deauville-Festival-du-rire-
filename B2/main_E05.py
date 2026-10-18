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


def start_of(performance):
    return datetime.fromisoformat(performance["start"])


def end_of(performance):
    start = start_of(performance)
    duration = timedelta(minutes=performance["duration_minutes"])
    return start + duration


def festival_day_of(performance):
    start = start_of(performance)
    return (start - timedelta(hours=6)).date()


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

def add_performance(festival):
    title = input("Title: ")
    artist_slug = input("Artist (slug): ")
    venue_slug = input("Venue (slug): ")
    start = input("Start (YYYY-MM-DDTHH:MM): ")
    duration_text = input("Duration (minutes): ")

    try:
        duration = int(duration_text)
    except ValueError:
        raise ValueError(
            f"'{duration_text}' is not a number of minutes."
        )

    new_performance = {
        "title": title,
        "kind": "solo",
        "artist": artist_slug,
        "venue": venue_slug,
        "start": start,
        "duration_minutes": duration
    }

    validate_performance(festival, new_performance)

    festival["performances"].append(new_performance)

    with open("data/festival.json", "w", encoding="utf-8") as file:
        json.dump(festival, file, ensure_ascii=False, indent=2)

    performance_id = (
        f"{venue_slug}-"
        f"{start[:10]}-"
        f"{start[11:16].replace(':', '')}"
    )

    print(f"Added: {performance_id}")

def performance_id(performance):
    start = start_of(performance)

    return (
        f"{performance['venue']}-"
        f"{start:%Y-%m-%d-%H%M}"
    )


def cancel_performance(festival, wanted_id):
    for performance in festival["performances"]:
        if performance_id(performance) == wanted_id:
            festival["performances"].remove(performance)

            with open("data/festival.json", "w", encoding="utf-8") as file:
                json.dump(festival, file, ensure_ascii=False, indent=2)

            print(f"Cancelled: {performance['title']}")
            return

    raise ValueError(f"Unknown performance '{wanted_id}'.")


def main():
    festival = load_festival()

    if len(sys.argv) == 1:
        print_summary(festival)

    elif sys.argv[1] == "venues":
        print_venues(festival)

    elif sys.argv[1] == "programme" and len(sys.argv) == 3:
        try:
            day = date.fromisoformat(sys.argv[2])
        except ValueError:
            raise ValueError(
                f"'{sys.argv[2]}' is not a day, use YYYY-MM-DD."
            )
        print_programme(festival, day)

    elif sys.argv[1] == "artist" and len(sys.argv) == 3:
        print_artist(festival, sys.argv[2])

    elif sys.argv[1] == "now" and len(sys.argv) == 3:
        moment = datetime.fromisoformat(sys.argv[2])
        print_now(festival, moment)

    elif sys.argv[1] == "add" and len(sys.argv) == 2:
        add_performance(festival)

    elif sys.argv[1] == "cancel" and len(sys.argv) == 3:
        cancel_performance(festival, sys.argv[2])

    else:
        print("Usage:")
        print("  uv run main.py")
        print("  uv run main.py venues")
        print("  uv run main.py programme YYYY-MM-DD")
        print("  uv run main.py artist ARTIST-SLUG")
        print("  uv run main.py now YYYY-MM-DDTHH:MM")
        print("  uv run main.py add")
        print("  uv run main.py cancel PERFORMANCE-ID")


try:
    main()
except ValueError as error:
    print(f"Error: {error}")
    sys.exit(1)