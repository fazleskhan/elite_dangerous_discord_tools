import src


def test_src_package_imports() -> None:
    assert hasattr(src, "__package__")
