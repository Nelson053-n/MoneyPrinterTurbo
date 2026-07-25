import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from webui.utils.text_utils import parse_chatterbox_voices, detect_audio_mime


class TestParseChatterboxVoices(unittest.TestCase):
    def test_empty_list(self):
        self.assertEqual(parse_chatterbox_voices([]), [])

    def test_none(self):
        self.assertEqual(parse_chatterbox_voices(None), [])

    def test_string_with_commas(self):
        self.assertEqual(
            parse_chatterbox_voices("a,b,c"), ["a", "b", "c"]
        )

    def test_string_with_surrounding_spaces(self):
        self.assertEqual(
            parse_chatterbox_voices(" a , b ,, c "), ["a", "b", "c"]
        )

    def test_list_with_empty_and_whitespace_elements(self):
        self.assertEqual(
            parse_chatterbox_voices(["a", "", "  ", " b "]), ["a", "b"]
        )

    def test_ready_list(self):
        self.assertEqual(
            parse_chatterbox_voices(["x", "y"]), ["x", "y"]
        )


class TestDetectAudioMime(unittest.TestCase):
    def test_wav(self):
        data = b"RIFF" + b"\x00\x00\x00\x00" + b"WAVE" + b"rest"
        self.assertEqual(detect_audio_mime("f", data), "audio/wav")

    def test_mp3_id3(self):
        data = b"ID3\x03\x00\x00\x00\x00\x00\x00\x00\x00"
        self.assertEqual(detect_audio_mime("f", data), "audio/mp3")

    def test_mp3_fffb(self):
        data = b"\xff\xfb\x90\x00" + b"padding0000"
        self.assertEqual(detect_audio_mime("f", data), "audio/mp3")

    def test_ogg(self):
        data = b"OggS" + b"\x00\x00\x00\x00\x00\x00\x00\x00"
        self.assertEqual(detect_audio_mime("f", data), "audio/ogg")

    def test_fallback_wav_extension(self):
        self.assertEqual(
            detect_audio_mime("sound.wav", b"unknownbytes"), "audio/wav"
        )

    def test_fallback_m4a_extension(self):
        self.assertEqual(
            detect_audio_mime("sound.m4a", b"unknownbytes"), "audio/mp4"
        )

    def test_fallback_aac_extension(self):
        self.assertEqual(
            detect_audio_mime("sound.aac", b"unknownbytes"), "audio/aac"
        )

    def test_fallback_ogg_extension(self):
        self.assertEqual(
            detect_audio_mime("sound.ogg", b"unknownbytes"), "audio/ogg"
        )

    def test_fallback_flac_extension(self):
        self.assertEqual(
            detect_audio_mime("sound.flac", b"unknownbytes"), "audio/flac"
        )

    def test_fallback_unknown_extension(self):
        self.assertEqual(
            detect_audio_mime("sound.xyz", b"unknownbytes"), "audio/mp3"
        )


if __name__ == "__main__":
    unittest.main()
