from datetime import date, timedelta
from fastapi import FastAPI
from festival import load_festival, slug
from fastapi.staticfiles import StaticFiles


app = FastAPI()


@app.get("/api/festival")
def get_festival():
    festival = load_festival()

    first_day = date.fromisoformat(festival["first_day"])
    last_day = date.fromisoformat(festival["last_day"])

    days = []
    current_day = first_day

    while current_day <= last_day:
        days.append(current_day.isoformat())
        current_day += timedelta(days=1)

    return {
        "name": festival["name"],
        "first_day": festival["first_day"],
        "last_day": festival["last_day"],
        "days": days
    }


@app.get("/api/venues")
def get_venues():
    festival = load_festival()

    venues = []

    for venue in festival["venues"]:
        venues.append({
            "slug": slug(venue["name"]),
            "name": venue["name"],
            "capacity": venue["capacity"],
            "address": venue["address"]
        })

    return venues


@app.get("/api/artists")
def get_artists():
    festival = load_festival()

    artists = []

    for artist in festival["artists"]:
        artists.append({
            "slug": slug(artist["name"]),
            "name": artist["name"],
            "bio": artist.get("bio", ""),
            "photo_url": artist.get("photo_url", "")
        })

    return sorted(artists, key=lambda artist: artist["slug"])

app.mount(
    "/",
    StaticFiles(directory="web/public", html=True),
    name="web"
)