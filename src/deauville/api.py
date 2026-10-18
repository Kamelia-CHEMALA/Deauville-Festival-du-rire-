import os
from datetime import date, datetime, timedelta

from fastapi import FastAPI, HTTPException, Response
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from deauville.festival import (
    ConflictError,
    FestivalError,
    InvalidError,
    Lineup,
    NotFoundError,
    SoloShow,
    Workshop,
    performance_id,
    slug,
)
from deauville.storage import JsonStorage


class ArtistCreate(BaseModel):
    name: str
    bio: str = ""
    photo_url: str = ""

class ParticipantCreate(BaseModel):
    name: str

class PerformanceCreate(BaseModel):
    kind: str
    title: str
    venue: str
    start: str
    duration_minutes: int
    description: str = ""
    artist: str | None = None
    min_age: int | None = None
    host: str | None = None
    acts: list[str] | None = None
    teacher: str | None = None
    max_participants: int | None = None


def create_app(storage):
    app = FastAPI()

    @app.exception_handler(FestivalError)
    async def festival_error_handler(request, exc):
        if isinstance(exc, NotFoundError):
            status_code = 404
        elif isinstance(exc, ConflictError):
            status_code = 409
        else:
            status_code = 422

        return JSONResponse(
            status_code=status_code,
            content={"detail": str(exc)}
        )

    @app.get("/api/festival")
    def get_festival():
        festival = storage.load()

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
        festival = storage.load()

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
        festival = storage.load()

        artists = []

        for artist in festival["artists"]:
            artists.append({
                "slug": slug(artist["name"]),
                "name": artist["name"],
                "bio": artist.get("bio", ""),
                "photo_url": artist.get("photo_url", "")
            })

        return sorted(artists, key=lambda artist: artist["slug"])

    @app.get("/api/artists/{artist_slug}")
    def get_artist(artist_slug: str):
        festival = storage.load()

        for artist in festival["artists"]:
            if slug(artist["name"]) == artist_slug:

                performances = []

                for performance in festival["performances"]:
                    view = performance.view(festival)

                    if any(
                        a["slug"] == artist_slug
                        for a in view["artists"]
                    ):
                        performances.append(view)

                performances.sort(key=lambda p: p["start"])

                return {
                    "slug": artist_slug,
                    "name": artist["name"],
                    "bio": artist.get("bio", ""),
                    "photo_url": artist.get("photo_url", ""),
                    "performances": performances
                }

        raise NotFoundError("Artist not found.")

    @app.get("/api/programme")
    def get_programme(day: date | None = None, venue: str | None = None):
        festival = storage.load()

        performances = festival["performances"]

        if day is not None:
            performances = [
                p for p in performances
                if p.festival_day() == day
            ]

        if venue:
            performances = [
                p for p in performances
                if p.venue == venue
            ]

        performances = sorted(
            performances,
            key=lambda p: p.start
        )

        return [p.view(festival) for p in performances]

    @app.get("/api/now")
    def get_now(at: datetime | None = None):
        festival = storage.load()

        moment = at if at is not None else datetime.now()

        now_playing = []
        up_next = []

        for performance in festival["performances"]:
            start = performance.start
            end = start + timedelta(minutes=performance.duration_minutes)

            if start <= moment < end:
                now_playing.append(performance.view(festival))

            elif start > moment:
                up_next.append(performance.view(festival))

        now_playing.sort(key=lambda p: p["start"])
        up_next.sort(key=lambda p: p["start"])

        return {
            "at": moment.isoformat(timespec="minutes"),
            "now_playing": now_playing,
            "up_next": up_next[:3]
        }


    @app.get("/api/performances/{performance_id_value}")
    def get_performance(performance_id_value: str):
        festival = storage.load()

        for performance in festival["performances"]:
            if performance_id(performance) == performance_id_value:
                return performance.view(festival)

        raise HTTPException(
            status_code=404,
            detail="Performance not found"
        )

    @app.post("/api/artists", status_code=201)
    def create_artist(data: ArtistCreate):
        festival = storage.load()

        artist = festival.add_artist(
            data.name,
            data.bio,
            data.photo_url
        )

        storage.save(festival)

        return {
            "slug": slug(artist["name"]),
            **artist
        }

    @app.post("/api/performances", status_code=201)
    def create_performance(data: PerformanceCreate):
        festival = storage.load()
        values = data.model_dump(exclude_none=True)

        kind = values.pop("kind")

        classes = {
            "solo": SoloShow,
            "lineup": Lineup,
            "workshop": Workshop
        }

        if kind not in classes:
            raise InvalidError("Unknown performance kind.")

        try:
            performance = classes[kind](**values)
        except (TypeError, ValueError) as error:
            raise InvalidError(str(error))

        festival.add_performance(performance)

        storage.save(festival)

        return performance.view(festival)

    @app.put("/api/performances/{performance_id_value}")
    def update_performance(
        performance_id_value: str,
        data: PerformanceCreate
    ):
        festival = storage.load()
        values = data.model_dump(exclude_none=True)

        kind = values.pop("kind")

        classes = {
            "solo": SoloShow,
            "lineup": Lineup,
            "workshop": Workshop
        }

        if kind not in classes:
            raise InvalidError("Unknown performance kind.")

        try:
            new_performance = classes[kind](**values)
        except (TypeError, ValueError) as error:
            raise InvalidError(str(error))

        festival.move_performance(
            performance_id_value,
            new_performance
        )

        storage.save(festival)

        return new_performance.view(festival)


    @app.delete("/api/performances/{performance_id_value}", status_code=204)
    def delete_performance(performance_id_value: str):
        festival = storage.load()

        festival.cancel_performance(performance_id_value)

        storage.save(festival)

        return Response(status_code=204)

    @app.post("/api/performances/{performance_id_value}/participants", status_code=201)
    def add_participant(performance_id_value: str, data: ParticipantCreate):
        festival = storage.load()

        workshop = None

        for performance in festival["performances"]:
            if performance_id(performance) == performance_id_value:
                workshop = performance
                break

        if workshop is None:
            raise NotFoundError("Performance not found.")

        if not isinstance(workshop, Workshop):
            raise InvalidError("This performance is not a workshop.")

        workshop.register_participant(festival, data.name)

        storage.save(festival)

        return workshop.view(festival)

    app.mount(
        "/admin",
        StaticFiles(directory="web/admin", html=True),
        name="admin"
    )

    app.mount(
        "/",
        StaticFiles(directory="web/public", html=True),
        name="web"
    )
    return app

app = create_app(
    JsonStorage(os.environ.get("DEAUVILLE_DATA", "data/festival.json"))
)

