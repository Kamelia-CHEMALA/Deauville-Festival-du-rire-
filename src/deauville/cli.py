import json
import os
import sys
from deauville.storage import JsonStorage
import uvicorn
from datetime import datetime, date
import deauville.festival
from deauville.storage import JsonStorage
from deauville.festival import (
    SoloShow,
    slug,
    load_festival,
    find_venue,
    find_artist,
    programme,
    start_of,
    end_of,
    festival_day_of,
    validate_performance,
    performance_id,
    FestivalError,
)



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
        venue = find_venue(festival, performance.venue)

        start = start_of(performance)
        end = end_of(performance)

        print(
            f"{start:%H:%M}-{end:%H:%M} | "
            f"{venue['name']} | "
            f"{performance.title} ({performance.kind})"
        )


def print_artist(festival, artist_slug):
    artist = find_artist(festival, artist_slug)

    if artist is None:
        print(f"No artist '{artist_slug}'.")
        return

    print(artist["name"])

    for performance in festival["performances"]:
        role = performance.role_of(artist_slug)

        if role is not None:
            venue = find_venue(festival, performance.venue)
            start = start_of(performance)
            end = end_of(performance)
            festival_day = festival_day_of(performance)

            print(
                f"{festival_day:%a %d} "
                f"{start:%H:%M}-{end:%H:%M} | "
                f"{venue['name']} | "
                f"{performance.title} ({role})"
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
        venue = find_venue(festival, performance.venue)
        end = end_of(performance)

        print(
            f"- {performance.title} at "
            f"{venue['name']}, until {end:%H:%M}"
        )

    print("Up next:")

    for performance in upcoming:
        venue = find_venue(festival, performance.venue)
        start = start_of(performance)
        end = end_of(performance)

        print(
            f"- {start:%H:%M}-{end:%H:%M} | "
            f"{venue['name']} | "
            f"{performance.title} ({performance.kind})"
        )


def save_festival(festival, storage):
    storage.save(festival)

    with open("data/festival.json", "w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2)


def add_performance(festival, storage):
    title = input("Title: ")
    artist_slug = input("Artist (slug): ")
    venue_slug = input("Venue (slug): ")
    start = input("Start (YYYY-MM-DDTHH:MM): ")
    duration_text = input("Duration (minutes): ")

    try:
        duration = int(duration_text)
    except ValueError:
        raise ValueError(
            f"'{duration_text}' is not a number of minutes.")

    new_performance = SoloShow(
        title=title,
        venue=venue_slug,
        start=start,
        duration_minutes=duration,
        artist=artist_slug
    )

    festival.add_performance(new_performance)
    save_festival(festival, storage)

    print(f"Added: {performance_id(new_performance)}")


def cancel_performance(festival, performance_id_value, storage):
    festival.cancel_performance(performance_id_value)
    save_festival(festival, storage)
    print(f"Cancelled {performance_id_value}")


def main():
    args = sys.argv[1:]
    data_path = "data/festival.json"

    if "--data" in args:
        index = args.index("--data")

        if index + 1 >= len(args):
            print("Error: --data requires a file path.")
            sys.exit(1)

        data_path = args[index + 1]
        del args[index:index + 2]

    os.environ["DEAUVILLE_DATA"] = data_path

    if args and args[0] == "serve":
        uvicorn.run(
            "deauville.api:app",
            host="127.0.0.1",
            port=8000
        )
        return

    storage = JsonStorage(data_path)
    festival = storage.load()

    try:
        if len(args) == 0:
            print_summary(festival)

        elif args[0] == "venues" and len(args) == 1:
            print_venues(festival)

        elif args[0] == "programme" and len(args) == 2:
            try:
                day = date.fromisoformat(args[1])
            except ValueError:
                raise FestivalError(
                    f"'{args[1]}' is not a day, use YYYY-MM-DD."
                )
            print_programme(festival, day)

        elif args[0] == "artist" and len(args) == 2:
            print_artist(festival, args[1])

        elif args[0] == "now" and len(args) == 2:
            try:
                moment = datetime.fromisoformat(args[1])
            except ValueError:
                raise FestivalError(
                    "Invalid date, use YYYY-MM-DDTHH:MM."
                )
            print_now(festival, moment)

        elif args[0] == "add" and len(args) == 1:
            add_performance(festival, storage)

        elif args[0] == "cancel" and len(args) == 2:
            cancel_performance(festival, args[1], storage)

        else:
            print("Usage:")
            print("  uv run deauville")
            print("  uv run deauville venues")
            print("  uv run deauville programme YYYY-MM-DD")
            print("  uv run deauville artist ARTIST-SLUG")
            print("  uv run deauville now YYYY-MM-DDTHH:MM")
            print("  uv run deauville add")
            print("  uv run deauville cancel PERFORMANCE-ID")
            print("  uv run deauville serve")
            print("  Add --data FILE to use another JSON file.")

    except FestivalError as error:
        print(f"Error: {error}")
        sys.exit(1)


if __name__ == "__main__":
    main()