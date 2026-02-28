import pdfeditor


def test_version_exists() -> None:
    assert pdfeditor.__version__ == "1.0.0"
