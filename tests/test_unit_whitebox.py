import os
import pytest
from lucent.config import Look, load_look, save_look, get_recent_sources, add_recent_source, save_session, load_session
from lucent.sources import normalize_source, is_url
from lucent import winapi
from lucent.viewers import create_viewer, TextViewer, ImageViewer, EmptyViewer


def test_sources_normalization(tmp_path):
    # URL normalization
    assert normalize_source("https://google.com") == "https://google.com"
    assert normalize_source("google.com") == "https://google.com"
    assert normalize_source("localhost:8000") == "https://localhost:8000"
    assert "duckduckgo.com/?q=" in normalize_source("python testing")

    # Local file normalization
    sample_file = tmp_path / "test.txt"
    sample_file.write_text("sample content")
    assert normalize_source(str(sample_file)) == str(sample_file.resolve())


def test_is_url():
    assert is_url("https://example.com") is True
    assert is_url("http://localhost:3000") is True
    assert is_url("file:///C:/path/to/file") is False
    assert is_url("not a url") is False


def test_look_persistence():
    look = Look(opacity=0.75, hue=180, on_top=True, hide_from_capture=False, click_through=True, invert_colors=True)
    save_look(look)
    loaded = load_look()
    assert loaded.opacity == 0.75
    assert loaded.hue == 180
    assert loaded.on_top is True
    assert loaded.hide_from_capture is False
    assert loaded.click_through is True
    assert loaded.invert_colors is True


def test_recent_sources_persistence():
    add_recent_source("https://example.com/1")
    add_recent_source("https://example.com/2")
    recent = get_recent_sources()
    assert "https://example.com/2" in recent
    assert "https://example.com/1" in recent
    assert recent[0] == "https://example.com/2"


def test_session_persistence():
    data = [
        {"source": "test.pdf", "geometry": [10, 20, 800, 600]},
        {"source": "https://example.com", "geometry": [100, 100, 400, 300]},
    ]
    save_session(data)
    loaded = load_session()
    assert len(loaded) == 2
    assert loaded[0]["source"] == "test.pdf"
    assert loaded[1]["geometry"] == [100, 100, 400, 300]


def test_viewers_factory(qapp, tmp_path):
    txt_file = tmp_path / "doc.txt"
    txt_file.write_text("Hello Lucent")
    viewer = create_viewer(str(txt_file))
    assert isinstance(viewer, TextViewer)

    with pytest.raises(ValueError):
        create_viewer(str(tmp_path / "non_existent_file.xyz_unknown"))
