from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from deauville.api import create_app
from deauville.storage import JsonStorage


def test_get_festival(tmp_path):
    # Créer une copie temporaire des données
    source = Path("data/festival.json")
    destination = tmp_path / "festival.json"
    destination.write_bytes(source.read_bytes())

    # Construire une API utilisant uniquement cette copie
    storage = JsonStorage(destination)
    app = create_app(storage)
    client = TestClient(app)

    # Faire une requête HTTP sans lancer de serveur
    response = client.get("/api/festival")

    assert response.status_code == 200

    data = response.json()
    assert "name" in data
    assert "first_day" in data
    assert "last_day" in data
    assert "days" in data


@pytest.fixture
def client(tmp_path):
    source = Path("data/festival.json")
    destination = tmp_path / "festival.json"
    destination.write_bytes(source.read_bytes())

    storage = JsonStorage(destination)
    return TestClient(create_app(storage))


def test_get_venues(client):
    response = client.get("/api/venues")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_artists(client):
    response = client.get("/api/artists")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_programme(client):
    response = client.get("/api/programme")

    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_programme_filter_day(client):
    response = client.get(
        "/api/programme",
        params={"day": "2027-06-11"}
    )

    assert response.status_code == 200

    performances = response.json()
    assert len(performances) > 0

    for performance in performances:
        assert performance["festival_day"] == "2027-06-11"


def test_programme_filter_venue(client):
    programme = client.get("/api/programme").json()

    assert programme, "Le programme doit contenir au moins un spectacle"

    venue = programme[0]["venue"]

    response = client.get(
        "/api/programme",
        params={"venue": venue}
    )

    assert response.status_code == 200

    for performance in response.json():
        assert performance["venue"] == venue


def test_performance_not_found(client):
    response = client.get("/api/performances/inconnu")

    assert response.status_code == 404


def test_get_artist_by_slug(client):
    artists = client.get("/api/artists").json()

    assert len(artists) > 0

    artist_slug = artists[0]["slug"]

    response = client.get(f"/api/artists/{artist_slug}")

    assert response.status_code == 200

    artist = response.json()

    assert artist["slug"] == artist_slug
    assert "name" in artist
    assert "performances" in artist
    assert isinstance(artist["performances"], list)


def test_get_unknown_artist(client):
    response = client.get("/api/artists/artiste-inexistant")

    assert response.status_code == 404

def test_now_at_specific_time(client):
    response = client.get(
        "/api/now",
        params={"at": "2027-06-11T21:00"}
    )

    assert response.status_code == 200

    data = response.json()

    assert data["at"] == "2027-06-11T21:00"
    assert isinstance(data["now_playing"], list)
    assert isinstance(data["up_next"], list)
    assert len(data["up_next"]) <= 3


def test_now_invalid_date(client):
    response = client.get(
        "/api/now",
        params={"at": "bonjour"}
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_now_without_parameter(client):
    response = client.get("/api/now")

    assert response.status_code == 200
    assert "at" in response.json()

def test_create_artist(client):
    response = client.post(
        "/api/artists",
        json={
            "name": "Alice Martin",
            "bio": "Humoriste",
            "photo_url": ""
        }
    )

    assert response.status_code == 201
    assert response.json()["slug"] == "alice-martin"

    # Vérifier que l'artiste a été enregistré
    artists = client.get("/api/artists").json()

    assert any(
        artist["slug"] == "alice-martin"
        for artist in artists
    )


def test_create_performance(client):
    # Créer un artiste pour notre spectacle
    artist_response = client.post(
        "/api/artists",
        json={"name": "Alice Martin"}
    )

    assert artist_response.status_code == 201

    # Créer un spectacle à un horaire libre
    response = client.post(
        "/api/performances",
        json={
            "kind": "solo",
            "title": "Spectacle test",
            "venue": "le-kiosque",
            "start": "2027-06-11T10:00",
            "duration_minutes": 60,
            "artist": "alice-martin"
        }
    )

    assert response.status_code == 201

    performance = response.json()
    assert performance["title"] == "Spectacle test"
    assert performance["kind"] == "solo"

    # Vérifier que le spectacle est enregistré
    saved = client.get(
        f"/api/performances/{performance['id']}"
    )

    assert saved.status_code == 200
    assert saved.json()["title"] == "Spectacle test"


def test_create_artist_missing_name(client):
    response = client.post(
        "/api/artists",
        json={"bio": "Sans nom"}
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)

def test_update_performance_changes_id(client):
    # Créer un artiste
    response = client.post(
        "/api/artists",
        json={"name": "Alice Martin"}
    )
    assert response.status_code == 201

    # Créer un spectacle
    body = {
        "kind": "solo",
        "title": "Spectacle initial",
        "venue": "le-kiosque",
        "start": "2027-06-11T10:00",
        "duration_minutes": 60,
        "artist": "alice-martin"
    }

    created = client.post("/api/performances", json=body)
    assert created.status_code == 201

    old_id = created.json()["id"]

    # Déplacer le spectacle à un autre horaire
    updated_body = {
        **body,
        "title": "Spectacle modifié",
        "start": "2027-06-11T11:00"
    }

    updated = client.put(
        f"/api/performances/{old_id}",
        json=updated_body
    )

    assert updated.status_code == 200

    new_id = updated.json()["id"]

    assert new_id != old_id
    assert updated.json()["title"] == "Spectacle modifié"

    # L'ancien identifiant ne doit plus exister
    assert client.get(
        f"/api/performances/{old_id}"
    ).status_code == 404

    # Le nouvel identifiant doit fonctionner
    assert client.get(
        f"/api/performances/{new_id}"
    ).status_code == 200


def test_delete_performance_twice(client):
    # Créer un artiste
    response = client.post(
        "/api/artists",
        json={"name": "Alice Martin"}
    )
    assert response.status_code == 201

    # Créer un spectacle
    body = {
        "kind": "solo",
        "title": "Spectacle à supprimer",
        "venue": "le-kiosque",
        "start": "2027-06-11T10:00",
        "duration_minutes": 60,
        "artist": "alice-martin"
    }

    created = client.post("/api/performances", json=body)
    assert created.status_code == 201

    performance_id = created.json()["id"]

    # Première suppression
    deleted = client.delete(
        f"/api/performances/{performance_id}"
    )

    assert deleted.status_code == 204

    # Le spectacle n'existe plus
    assert client.get(
        f"/api/performances/{performance_id}"
    ).status_code == 404

    # Deuxième suppression : erreur 404
    deleted_again = client.delete(
        f"/api/performances/{performance_id}"
    )

    assert deleted_again.status_code == 404


def test_duplicate_artist(client):
    body = {"name": "Alice Martin"}

    first = client.post("/api/artists", json=body)
    assert first.status_code == 201

    second = client.post("/api/artists", json=body)
    assert second.status_code == 409
    assert isinstance(second.json()["detail"], str)


def test_invalid_performance_duration(client):
    body = {
        "kind": "solo",
        "title": "Spectacle invalide",
        "venue": "le-kiosque",
        "start": "2027-06-11T10:00",
        "duration_minutes": 400,
        "artist": "nora-lebrun"
    }

    response = client.post("/api/performances", json=body)

    assert response.status_code == 422
    assert "detail" in response.json()


def test_put_conflict_preserves_original(client):
    # Créer un artiste
    artist = client.post(
        "/api/artists",
        json={"name": "Alice Martin"}
    )
    assert artist.status_code == 201

    body = {
        "kind": "solo",
        "title": "Premier spectacle",
        "venue": "le-kiosque",
        "start": "2027-06-11T10:00",
        "duration_minutes": 60,
        "artist": "alice-martin"
    }

    # Créer un premier spectacle
    first = client.post("/api/performances", json=body)
    assert first.status_code == 201

    first_id = first.json()["id"]

    # Créer un deuxième spectacle à un autre horaire
    second_body = {
        **body,
        "title": "Deuxième spectacle",
        "start": "2027-06-11T12:00"
    }

    second = client.post(
        "/api/performances",
        json=second_body
    )
    assert second.status_code == 201

    second_id = second.json()["id"]

    # Essayer de déplacer le premier sur le créneau du deuxième
    conflicting_body = {
        **body,
        "start": "2027-06-11T12:00"
    }

    response = client.put(
        f"/api/performances/{first_id}",
        json=conflicting_body
    )

    assert response.status_code == 409

    # Le premier spectacle doit rester inchangé
    original = client.get(
        f"/api/performances/{first_id}"
    )

    assert original.status_code == 200
    assert original.json()["start"] == "2027-06-11T10:00"

    # Le deuxième spectacle doit également exister
    assert client.get(
        f"/api/performances/{second_id}"
    ).status_code == 200


def test_workshop_full(client):
    # Créer un professeur
    artist = client.post(
        "/api/artists",
        json={"name": "Alice Martin"}
    )
    assert artist.status_code == 201

    # Créer un atelier avec une seule place
    body = {
        "kind": "workshop",
        "title": "Atelier test",
        "venue": "le-kiosque",
        "start": "2027-06-11T10:00",
        "duration_minutes": 60,
        "teacher": "alice-martin",
        "max_participants": 1
    }

    created = client.post("/api/performances", json=body)

    print("ERREUR ATELIER :", created.status_code, created.json())

    assert created.status_code == 201

    workshop_id = created.json()["id"]

    # Première inscription : acceptée
    first = client.post(
        f"/api/performances/{workshop_id}/participants",
        json={"name": "Marie"}
    )

    assert first.status_code == 201
    assert first.json()["places_left"] == 0

    # Deuxième inscription : atelier complet
    second = client.post(
        f"/api/performances/{workshop_id}/participants",
        json={"name": "Paul"}
    )

    assert second.status_code == 409
    assert isinstance(second.json()["detail"], str)

    # Vérifier que Paul n'a pas été inscrit
    saved = client.get(
        f"/api/performances/{workshop_id}"
    )

    assert saved.status_code == 200
    assert saved.json()["participants"] == ["Marie"]

def test_storage_read_error(tmp_path):
    # Le fichier n'existe pas
    storage = JsonStorage(tmp_path / "missing.json")

    client = TestClient(
        create_app(storage),
        raise_server_exceptions=False
    )

    response = client.get("/api/festival")

    assert response.status_code == 500


def test_storage_write_error(tmp_path):
    # Une copie temporaire des données
    source = Path("data/festival.json")
    destination = tmp_path / "festival.json"
    destination.write_bytes(source.read_bytes())

    class FailingStorage(JsonStorage):
        def save(self, festival):
            raise OSError("Impossible d'écrire le fichier")

    storage = FailingStorage(destination)

    client = TestClient(
        create_app(storage),
        raise_server_exceptions=False
    )

    response = client.post(
        "/api/artists",
        json={"name": "Alice Martin"}
    )

    assert response.status_code == 500



def test_storage_read_error(tmp_path):
    storage = JsonStorage(tmp_path / "missing.json")

    client = TestClient(
        create_app(storage),
        raise_server_exceptions=False
    )

    response = client.get("/api/festival")
    assert response.status_code == 500


def test_storage_write_error(tmp_path):
    source = Path("data/festival.json")
    destination = tmp_path / "festival.json"
    destination.write_bytes(source.read_bytes())

    class FailingStorage(JsonStorage):
        def save(self, festival):
            raise OSError("Cannot write data")

    client = TestClient(
        create_app(FailingStorage(destination)),
        raise_server_exceptions=False
    )

    response = client.post(
        "/api/artists",
        json={"name": "Alice Martin"}
    )

    assert response.status_code == 500


def test_invalid_day_format(client):
    response = client.get(
        "/api/programme",
        params={"day": "June 11"}
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_unknown_venue(client):
    response = client.post(
        "/api/performances",
        json={
            "kind": "solo",
            "title": "Unknown venue",
            "venue": "venue-inconnue",
            "start": "2027-06-11T10:00",
            "duration_minutes": 60,
            "artist": "nora-lebrun"
        }
    )

    assert response.status_code == 404


def test_unknown_artist_in_performance(client):
    response = client.post(
        "/api/performances",
        json={
            "kind": "solo",
            "title": "Unknown artist",
            "venue": "le-kiosque",
            "start": "2027-06-11T10:00",
            "duration_minutes": 60,
            "artist": "artiste-inconnu"
        }
    )

    assert response.status_code == 404


def test_empty_artist_name(client):
    response = client.post(
        "/api/artists",
        json={"name": ""}
    )

    assert response.status_code == 422


def test_performance_outside_festival(client):
    response = client.post(
        "/api/performances",
        json={
            "kind": "solo",
            "title": "Outside festival",
            "venue": "le-kiosque",
            "start": "2028-01-01T10:00",
            "duration_minutes": 60,
            "artist": "nora-lebrun"
        }
    )

    assert response.status_code == 409


def test_participant_on_non_workshop(client):
    artist = client.post(
        "/api/artists",
        json={"name": "Alice Martin"}
    )
    assert artist.status_code == 201

    created = client.post(
        "/api/performances",
        json={
            "kind": "solo",
            "title": "Solo test",
            "venue": "le-kiosque",
            "start": "2027-06-11T10:00",
            "duration_minutes": 60,
            "artist": "alice-martin"
        }
    )
    assert created.status_code == 201

    performance_id = created.json()["id"]

    response = client.post(
        f"/api/performances/{performance_id}/participants",
        json={"name": "Marie"}
    )

    assert response.status_code == 422


def test_participant_unknown_performance(client):
    response = client.post(
        "/api/performances/inconnu/participants",
        json={"name": "Marie"}
    )

    assert response.status_code == 404


def test_missing_performance_field(client):
    response = client.post(
        "/api/performances",
        json={
            "kind": "solo",
            "title": "Incomplete"
        }
    )

    assert response.status_code == 422
    assert isinstance(response.json()["detail"], list)


def test_now_results_are_correct(client):
    programme = client.get("/api/programme").json()
    assert programme

    # On choisit le début d'une représentation existante.
    moment = programme[0]["start"]

    response = client.get(
        "/api/now",
        params={"at": moment}
    )

    assert response.status_code == 200

    data = response.json()

    assert any(
        p["id"] == programme[0]["id"]
        for p in data["now_playing"]
    )

    assert len(data["up_next"]) <= 3

    for performance in data["up_next"]:
        assert performance["start"] > moment
