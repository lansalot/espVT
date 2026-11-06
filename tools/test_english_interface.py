"""Check terminal-owned labels and their fixed-width navigation layout."""

import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RENDERER = (ROOT / "main" / "vt_scene_renderer.cpp").read_text(encoding="utf-8")
SERVER = (ROOT / "main" / "isobus_terminal_server.cpp").read_text(encoding="utf-8")


class EnglishInterfaceTests(unittest.TestCase):
    def test_navigation_labels_fit_buttons(self):
        menu = RENDERER.split("constexpr NavigationItem ITEMS[] = {", 1)[1].split("};", 1)[0]
        labels = re.findall(r'\{\s*"([^"]+)",\s*vt_scene_renderer::TerminalAction::(\w+)', menu)
        self.assertEqual(
            dict((action, label) for label, action in labels),
            {
                "ShowMachines": "MACHINES",
                "ShowTerminal": "TERMINAL",
                "ShowIsobus": "ISOBUS",
                "ShowAuxN": "AUX-N",
                "ShowGnss": "GNSS / SECT",
                "ShowAudio": "AUDIO",
                "ShowInformation": "INFORMATION",
            },
        )
        for label, _ in labels:
            self.assertLessEqual(len(label) * 12 + 20, 200 - 24, label)

    def test_settings_and_editor_use_english_labels(self):
        for label in (
            "MACHINE LANGUAGE: ENGLISH   COUNTRY: GB",
            "DATE: DD/MM/YYYY",
            "DECIMAL SYMBOL: COMMA",
            "ENTER NUMBER",
            "ENTER TEXT",
            "SELECT ITEM",
        ):
            self.assertIn(f'"{label}"', RENDERER)

    def test_machine_language_still_sent_over_isobus(self):
        self.assertIn('language_code = "en";', SERVER)
        self.assertIn("language.set_language_code(language_code);", SERVER)
        self.assertIn("language.send_language_command()", SERVER)
        self.assertIn('vt_scene_renderer::set_notice("VT TERMINAL IDENTIFICATION")', SERVER)
        self.assertIn('"AUX ASSIGNMENT SENT"', SERVER)


if __name__ == "__main__":
    unittest.main()
