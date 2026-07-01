from io import BytesIO

from meeting_summarizer.transcribe import _iter_decoded_lines, _read_json_text


def test_iter_decoded_lines_replaces_invalid_bytes():
    stream = BytesIO(b"progress = 15%\n\xff\xfebroken\n")

    lines = list(_iter_decoded_lines(stream))

    assert lines[0] == "progress = 15%"
    assert "broken" in lines[1]


def test_read_json_text_replaces_invalid_bytes(tmp_path):
    path = tmp_path / "audio.json"
    path.write_bytes(b'{"result":{"language":"ko"},"transcription":[{"text":"hi\xffthere"}]}')

    text = _read_json_text(path)

    assert "hi" in text
    assert "\ufffd" in text
