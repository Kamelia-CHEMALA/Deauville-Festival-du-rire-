import json
import sys
import unicodedata

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
        if performance["start"][:10] == day:
            performances.append(performance)

    return performances


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
    print(f"Programme for {day}:")

    for performance in programme(festival, day):
        venue = find_venue(festival, performance["venue"])
        time = performance["start"][11:16]

        print(
            f"{time} | {venue['name']} | "
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
            start = performance["start"].replace("T", " ")

            print(
                f"{start} | {venue['name']} | "
                f"{performance['title']} ({role})"
            )

festival = load_festival()

if len(sys.argv) == 1:
    print_summary(festival)

elif sys.argv[1] == "venues":
    print_venues(festival)

elif sys.argv[1] == "programme" and len(sys.argv) == 3:
    print_programme(festival, sys.argv[2])

elif sys.argv[1] == "artist" and len(sys.argv) == 3:
    print_artist(festival, sys.argv[2])

else:
    print("Usage:")
    print("  uv run main.py")
    print("  uv run main.py venues")
    print("  uv run main.py programme YYYY-MM-DD")
    print("  uv run main.py artist ARTIST-SLUG")
