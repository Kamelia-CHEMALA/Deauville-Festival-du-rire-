import json
from abc import ABC, abstractmethod
from pathlib import Path


class Storage(ABC):
    @abstractmethod
    def load(self):
        pass

    @abstractmethod
    def save(self, festival):
        pass


class JsonStorage(Storage):
    def __init__(self, path="data/festival.json"):
        self.path = Path(path)

    def load(self):
        from deauville.festival import load_festival
        return load_festival(self.path)

    def save(self, festival):
        data = dict(festival)
        data["performances"] = [
            p.to_dict() for p in festival["performances"]
        ]

        self.path.write_text(
            json.dumps(data, ensure_ascii=False, indent=2),
            encoding="utf-8"
        )