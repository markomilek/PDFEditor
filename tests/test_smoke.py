import pdfeditor


def test_version_exists() -> None:
    assert hasattr(pdfeditor, "__version__")
