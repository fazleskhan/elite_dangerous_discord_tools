from typing import get_type_hints

import ed_protocols


def test_protocol_aliases_and_annotations_exist() -> None:
    assert ed_protocols.SystemInfo == dict[str, ed_protocols.Any]
    hints = get_type_hints(ed_protocols.DatasourceProtocol.init_datasource)
    assert hints["import_dir"] == str
    assert "return" in get_type_hints(ed_protocols.PathProtocol.run)


def test_protocol_classes_are_available() -> None:
    assert hasattr(ed_protocols, "LoggingProtocol")
    assert hasattr(ed_protocols, "RouteServiceProtocol")
    assert hasattr(ed_protocols, "BulkLoadProtocol")
