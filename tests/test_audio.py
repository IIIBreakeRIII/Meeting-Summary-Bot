from pathlib import Path

import pytest

from meeting_summarizer.audio import (
    SUPPORTED_AUDIO_SUFFIXES,
    UnsupportedAudioFormatError,
    ensure_supported_audio_file,
)


def test_m4a_is_supported():
    assert ".m4a" in SUPPORTED_AUDIO_SUFFIXES
    ensure_supported_audio_file(Path("meeting.m4a"))


def test_aiff_is_supported():
    assert ".aiff" in SUPPORTED_AUDIO_SUFFIXES
    ensure_supported_audio_file(Path("meeting.aiff"))


def test_unsupported_audio_format_raises():
    with pytest.raises(UnsupportedAudioFormatError):
        ensure_supported_audio_file(Path("meeting.txt"))
