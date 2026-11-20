from .catalog import Catalog, CatalogError, Classroom
from .constants import DEFAULT_FILE


def main() -> None:
    first = Classroom("a101", "Аудитория 101", "лекционная", 2020, 30, True)
    second = Classroom("b202", "Компьютерный класс", "компьютерная", 2023, 20, False)

    catalog = Catalog()
    catalog.add(first)
    catalog.add(second)

    print("Все аудитории:")
    for item in catalog:
        print(item.name)

    print("Количество:", len(catalog))
    print("Есть ID a101:", "a101" in catalog)
    print("По ID:", catalog.get("a101").name)

    by_category = catalog.find_by_category("лекционная")
    by_name = catalog.find_by_name("КЛАСС")
    print("По категории:", [item.name for item in by_category])
    print("По названию:", [item.name for item in by_name])

    catalog.save(DEFAULT_FILE)
    loaded = Catalog()
    loaded.load(DEFAULT_FILE)
    loaded.remove("a101")
    print("После загрузки и удаления a101:", len(loaded))


if __name__ == "__main__":
    try:
        main()
    except CatalogError as error:
        print("Ошибка:", error)
        raise SystemExit(2)
