import json
from abc import ABC, abstractmethod
from pathlib import Path

from deauville.festival import Festival, load_festival


class Storage(ABC):
    """Define the interface for loading and saving festival data."""

    @abstractmethod
    def load(self) -> Festival:
        """Load festival data from storage."""
        pass

    @abstractmethod
    def save(self, festival: Festival) -> None:
        """Save festival data to storage."""
        pass


class JsonStorage(Storage):
    """Store festival data in a JSON file."""

    def __init__(self, path: str | Path = "data/festival.json") -> None:
        """Initialize storage with the JSON file path."""
        self.path = Path(path)

    def load(self) -> Festival:
        """Read the JSON file and return a Festival object."""
        return load_festival(self.path)

    def save(self, festival: Festival) -> None:
        """Serialize and save the festival to the JSON file."""
        data = dict(festival)
        data["performances"] = [
            performance.to_dict() for performance in festival["performances"]
        ]

        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
