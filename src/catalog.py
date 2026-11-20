import json
from collections.abc import Iterator
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path

from .constants import FORMAT_VERSION


class CatalogError(Exception):
    pass


class InvalidClassroomError(CatalogError):
    pass


class DuplicateIdError(CatalogError):
    pass


class ItemNotFoundError(CatalogError):
    pass


class UnsupportedFormatVersionError(CatalogError):
    pass


class CorruptedFileError(CatalogError):
    pass


@dataclass(frozen=True)
class Classroom:
    item_id: str
    name: str
    category: str
    year: int
    capacity: int
    has_projector: bool

    def __post_init__(self) -> None:
        for value in (self.item_id, self.name, self.category):
            if not isinstance(value, str) or not value.strip():
                raise InvalidClassroomError(
                    "ID, название и категория должны быть непустыми строками."
                )

        if type(self.year) is not int or not 1 <= self.year <= date.today().year:
            raise InvalidClassroomError("Укажи год от 1 до текущего года.")

        if type(self.capacity) is not int or self.capacity < 1:
            raise InvalidClassroomError("Количество мест должно быть целым и больше нуля.")

        if type(self.has_projector) is not bool:
            raise InvalidClassroomError("Для проектора укажи True или False.")


class Catalog:
    def __init__(self) -> None:
        self._items: dict[str, Classroom] = {}

    def add(self, item: Classroom) -> None:
        if not isinstance(item, Classroom):
            raise InvalidClassroomError("В каталог можно добавить только аудиторию.")
        if item.item_id in self._items:
            raise DuplicateIdError(f"ID уже существует: {item.item_id}")
        self._items[item.item_id] = item

    def get(self, item_id: str) -> Classroom:
        if item_id not in self._items:
            raise ItemNotFoundError(f"Аудитория не найдена: {item_id}")
        return self._items[item_id]

    def remove(self, item_id: str) -> None:
        if item_id not in self._items:
            raise ItemNotFoundError(f"Аудитория не найдена: {item_id}")
        del self._items[item_id]

    def find_by_category(self, category: str) -> list[Classroom]:
        result = []
        for item in self._items.values():
            if item.category == category:
                result.append(item)
        return result

    def find_by_name(self, query: str) -> list[Classroom]:
        query = query.casefold()
        result = []
        for item in self._items.values():
            if query in item.name.casefold():
                result.append(item)
        return result

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[Classroom]:
        return iter(self._items.values())

    def __contains__(self, item_id: object) -> bool:
        return isinstance(item_id, str) and item_id in self._items

    def save(self, filename: str | Path) -> None:
        rows = []
        for item in self:
            rows.append(asdict(item))
        data = {"format_version": FORMAT_VERSION, "items": rows}

        try:
            with open(filename, "w", encoding="utf-8") as file:
                json.dump(data, file, ensure_ascii=False, indent=4)
        except OSError as error:
            raise CatalogError("Не удалось сохранить каталог.") from error

    def load(self, filename: str | Path) -> None:
        try:
            with open(filename, encoding="utf-8") as file:
                data = json.load(file)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise CorruptedFileError("Не удалось прочитать JSON.") from error

        if not isinstance(data, dict):
            raise CorruptedFileError("Корень JSON должен быть объектом.")

        version = data.get("format_version")
        if type(version) is not int:
            raise CorruptedFileError("format_version должен быть целым числом.")
        if version != FORMAT_VERSION:
            raise UnsupportedFormatVersionError(f"Версия не поддерживается: {version}")

        rows = data.get("items")
        if not isinstance(rows, list):
            raise CorruptedFileError("items должен быть списком.")

        temporary = Catalog()
        for row in rows:
            if not isinstance(row, dict):
                raise CorruptedFileError("Запись об аудитории должна быть объектом.")
            try:
                item = Classroom(**row)
                temporary.add(item)
            except (TypeError, InvalidClassroomError, DuplicateIdError) as error:
                raise CorruptedFileError(f"Ошибка в записи об аудитории: {error}") from error

        self._items = temporary._items
