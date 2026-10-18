import json

with open("data/festival.json", encoding="utf-8") as file:
    festival = json.load(file)

#EOO
print(festival["name"])
print(f"From {festival['first_day']} to {festival['last_day']}")
print(
    f"{len(festival['venues'])} venues, "
    f"{len(festival['artists'])} artists, "
    f"{len(festival['performances'])} performances"
)

#EO1
#01
print("\nVenues:")

total_seats = 0

for venue in festival["venues"]:
    print(f"- {venue['name']}: {venue['capacity']} seats ({venue['address']})")
    total_seats += venue["capacity"]

print(f"Total: {total_seats} seats")

#02
print()

kinds = {}

for performance in festival["performances"]:
    kind = performance["kind"]

    if kind not in kinds:
        kinds[kind] = 0

    kinds[kind] += 1

for kind, count in kinds.items():
    print(f"{kind}: {count}")

#03
print("\nAt Le Kiosque:")

for performance in festival["performances"]:
    if performance["venue"] == "le-kiosque":
        print(f"- {performance['start']} {performance['title']}")

#04
longest = festival["performances"][0]

for performance in festival["performances"]:
    if performance["duration_minutes"] > longest["duration_minutes"]:
        longest = performance

print(f"\nLongest: {longest['title']} ({longest['duration_minutes']} min)")

#05
print()

for performance in festival["performances"]:
    if performance["kind"] == "workshop":
        day = performance["start"][:10]
        registered = len(performance["participants"])

        print(
            f"{performance['title']} on {day}: "
            f"{registered}/{performance['max_participants']} registered"
        )

#06
artist_counts = {}

for performance in festival["performances"]:

    if "artist" in performance:
        artist = performance["artist"]
        artist_counts[artist] = artist_counts.get(artist, 0) + 1

    if "host" in performance:
        host = performance["host"]
        artist_counts[host] = artist_counts.get(host, 0) + 1

    if "acts" in performance:
        for artist in performance["acts"]:
            artist_counts[artist] = artist_counts.get(artist, 0) + 1

    if "teacher" in performance:
        teacher = performance["teacher"]
        artist_counts[teacher] = artist_counts.get(teacher, 0) + 1

max_count = max(artist_counts.values())

top_artists = []

for artist, count in artist_counts.items():
    if count == max_count:
        top_artists.append(artist)

print(f"\nOn stage {max_count} times: {', '.join(top_artists)}")


#E02
days = []

for performance in festival["performances"]:
    day = performance["start"][:10]

    if day not in days:
        days.append(day)

days.sort()
day = input("\nDay (YYYY-MM-DD): ")

while day not in days:
    print(f"No performance on '{day}'. Days: {', '.join(days)}")
    day = input("Day (YYYY-MM-DD): ")

print(f"Programme for {day}:")

for performance in festival["performances"]:
    if performance["start"][:10] == day:

        venue_name = ""

        for venue in festival["venues"]:
            slug = venue["name"].lower().replace(" ", "-").replace("é", "e").replace("â", "a")

            if slug == performance["venue"]:
                venue_name = venue["name"]

        time = performance["start"][11:16]

        print(
            f"{time} | {venue_name} | "
            f"{performance['title']} ({performance['kind']})"
        )



