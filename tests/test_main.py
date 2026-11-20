import json

from src.constants import DEFAULT_FILE, FORMAT_VERSION
from src.main import main


def test_main(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)

    main()

    output = capsys.readouterr().out
    assert "Количество: 2" in output
    assert "Есть ID a101: True" in output
    assert "По категории: ['Аудитория 101']" in output
    assert "По названию: ['Компьютерный класс']" in output
    assert "После загрузки и удаления a101: 1" in output

    path = tmp_path / DEFAULT_FILE
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["format_version"] == FORMAT_VERSION
    assert [item["item_id"] for item in data["items"]] == ["a101", "b202"]