import json
from dataclasses import FrozenInstanceError, asdict
from datetime import date
from pathlib import Path

import pytest

from src.catalog import (
    Catalog,
    Classroom,
    CorruptedFileError,
    DuplicateIdError,
    InvalidClassroomError,
    ItemNotFoundError,
    UnsupportedFormatVersionError,
)
from src.constants import FORMAT_VERSION


def make_room(item_id: str = "a101") -> Classroom:
    return Classroom(item_id, "Аудитория 101", "лекционная", 2020, 30, True)


def write_json(path: Path, data: object) -> None:
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")


def test_classroom() -> None:
    room = make_room()
    assert room.item_id == "a101"
    assert room.name == "Аудитория 101"
    assert room.category == "лекционная"
    assert room.year == 2020
    assert room.capacity == 30
    assert room.has_projector is True


@pytest.mark.parametrize(
    "field,value",
    [
        ("item_id", ""),
        ("item_id", "   "),
        ("item_id", 123),
        ("name", ""),
        ("name", None),
        ("category", " "),
        ("category", 123),
        ("year", 0),
        ("year", date.today().year + 1),
        ("year", "2020"),
        ("year", True),
        ("year", 2020.5),
        ("capacity", 0),
        ("capacity", -1),
        ("capacity", True),
        ("capacity", 2.5),
        ("has_projector", "да"),
        ("has_projector", 1),
    ],
)
def test_invalid_classroom(field: str, value: object) -> None:
    fields = asdict(make_room())
    fields[field] = value
    with pytest.raises(InvalidClassroomError):
        Classroom(**fields)


@pytest.mark.parametrize("year", [1, date.today().year])
def test_valid_boundaries(year: int) -> None:
    room = Classroom("a101", "Аудитория 101", "лекционная", year, 1, False)
    assert room.year == year
    assert room.capacity == 1
    assert room.has_projector is False


def test_frozen_classroom() -> None:
    with pytest.raises(FrozenInstanceError):
        setattr(make_room(), "item_id", "changed")


def test_add_get_remove() -> None:
    catalog = Catalog()
    room = make_room()
    catalog.add(room)
    assert catalog.get("a101") == room
    assert "a101" in catalog
    assert len(catalog) == 1

    catalog.remove("a101")
    assert "a101" not in catalog
    assert len(catalog) == 0
    assert list(catalog) == []
    assert catalog.find_by_category(room.category) == []
    assert catalog.find_by_name(room.name) == []


def test_missing_id() -> None:
    catalog = Catalog()
    with pytest.raises(ItemNotFoundError):
        catalog.get("missing")
    with pytest.raises(ItemNotFoundError):
        catalog.remove("missing")


def test_duplicate_id() -> None:
    catalog = Catalog()
    room = make_room()
    catalog.add(room)
    with pytest.raises(DuplicateIdError):
        catalog.add(make_room())
    assert len(catalog) == 1
    assert catalog.get("a101") is room


def test_search() -> None:
    catalog = Catalog()
    first = make_room()
    second = Classroom("b202", "Компьютерный КЛАСС", "компьютерная", 2023, 20, False)
    third = make_room("c303")
    for room in (first, second, third):
        catalog.add(room)

    assert catalog.find_by_category("лекционная") == [first, third]
    assert catalog.find_by_category("спортивная") == []
    assert catalog.find_by_name("класс") == [second]
    assert catalog.find_by_name("КлАсС") == [second]
    assert catalog.find_by_name("нет совпадения") == []
    assert catalog.find_by_name("") == [first, second, third]


def test_search_returns_new_lists() -> None:
    catalog = Catalog()
    room = make_room()
    catalog.add(room)

    by_name = catalog.find_by_name("аудитория")
    by_category = catalog.find_by_category("лекционная")
    by_name.clear()
    by_category.append(make_room("extra"))

    assert list(catalog) == [room]
    assert catalog.find_by_name("аудитория") == [room]
    assert catalog.find_by_category("лекционная") == [room]


def test_iteration_order() -> None:
    catalog = Catalog()
    first = make_room("b")
    second = make_room("a")
    for room in (first, second):
        catalog.add(room)

    assert list(catalog) == [first, second]
    catalog.remove("b")
    catalog.add(first)
    assert list(catalog) == [second, first]


def test_save_and_load(tmp_path: Path) -> None:
    catalog = Catalog()
    first = make_room()
    second = Classroom("b202", "Компьютерный класс", "компьютерная", 2023, 20, False)
    catalog.add(first)
    catalog.add(second)
    path = tmp_path / "catalog.json"
    catalog.save(path)

    document = json.loads(path.read_text(encoding="utf-8"))
    assert document["format_version"] == FORMAT_VERSION
    assert document["items"] == [asdict(first), asdict(second)]

    loaded = Catalog()
    loaded.add(make_room("old"))
    loaded.load(path)
    assert list(loaded) == [first, second]
    assert loaded.get("b202") == second
    assert "old" not in loaded


def test_empty_catalog(tmp_path: Path) -> None:
    path = tmp_path / "empty.json"
    Catalog().save(path)

    catalog = Catalog()
    catalog.add(make_room())
    catalog.load(path)
    assert len(catalog) == 0


def test_broken_json(tmp_path: Path) -> None:
    path = tmp_path / "broken.json"
    path.write_text("{broken", encoding="utf-8")

    catalog = Catalog()
    room = make_room()
    catalog.add(room)
    with pytest.raises(CorruptedFileError):
        catalog.load(path)
    assert list(catalog) == [room]


@pytest.mark.parametrize(
    "document",
    [
        [],
        {},
        {"format_version": "1", "items": []},
        {"format_version": True, "items": []},
        {"format_version": 1.0, "items": []},
        {"format_version": FORMAT_VERSION},
        {"format_version": FORMAT_VERSION, "items": {}},
        {"format_version": FORMAT_VERSION, "items": [123]},
    ],
)
def test_invalid_json_structure(tmp_path: Path, document: object) -> None:
    path = tmp_path / "invalid.json"
    write_json(path, document)
    with pytest.raises(CorruptedFileError):
        Catalog().load(path)


def test_unsupported_version(tmp_path: Path) -> None:
    path = tmp_path / "version.json"
    write_json(path, {"format_version": FORMAT_VERSION + 1, "items": []})

    catalog = Catalog()
    room = make_room()
    catalog.add(room)
    with pytest.raises(UnsupportedFormatVersionError):
        catalog.load(path)
    assert list(catalog) == [room]


@pytest.mark.parametrize("problem", ["capacity", "duplicate", "missing_field"])
def test_failed_load_keeps_old_catalog(tmp_path: Path, problem: str) -> None:
    catalog = Catalog()
    old_room = make_room("old")
    catalog.add(old_room)

    first = asdict(make_room("new1"))
    second = asdict(make_room("new2"))
    if problem == "capacity":
        second["capacity"] = 0
    elif problem == "duplicate":
        second["item_id"] = "new1"
    else:
        del second["name"]

    path = tmp_path / "partial.json"
    write_json(path, {"format_version": FORMAT_VERSION, "items": [first, second]})
    with pytest.raises(CorruptedFileError):
        catalog.load(path)
    assert list(catalog) == [old_room]
    assert catalog.get("old") is old_room
