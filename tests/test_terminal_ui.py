"""Terminal presentation contract: small, truthful, safe for pipes and setup."""
import io
import os
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from liveclip.terminal_ui import SessionUI, _clip_message, _elapsed, rich_terminal, setup_line, main


class TerminalUITests(unittest.TestCase):
    def test_plain_setup_and_no_fake_progress(self):
        output = io.StringIO()
        setup_line("boot", stream=output)
        setup_line("step", "03", "Dependencies", "working", stream=output)
        setup_line("step", "03", "Dependencies", "ok", stream=output)
        self.assertIn("@S2zxx0zxx", output.getvalue())
        self.assertIn("Dependencies  working", output.getvalue())
        self.assertNotIn("%", output.getvalue())
        self.assertFalse(rich_terminal(output))

    def test_no_color_and_plain_controls(self):
        class FakeTTY(io.StringIO):
            def isatty(self):
                return True
        stream = FakeTTY()
        with patch.dict(os.environ, {"NO_COLOR": "1"}):
            self.assertFalse(rich_terminal(stream))
        with patch.dict(os.environ, {"LIVECLIP_PLAIN": "1"}):
            self.assertFalse(rich_terminal(stream))
        with patch.dict(os.environ, {"TERM": "dumb"}):
            self.assertFalse(rich_terminal(stream))

    def test_pipe_event_compatibility(self):
        output = io.StringIO()
        with TemporaryDirectory() as tmp:
            ui = SessionUI("analyze", Path(tmp), stream=output, clock=lambda: 30.0)
            ui.start()
            ui.event("candidate", "peak 01")
            ui.event("highlight", "exported")
            ui.event("error", "engine failed")
            ui.close()
        self.assertIn("Session:", output.getvalue())
        self.assertIn("[candidate] peak 01", output.getvalue())
        self.assertIn("[highlight] exported", output.getvalue())
        self.assertIn("[error] engine failed", output.getvalue())
        self.assertEqual((ui.candidates, ui.highlight_events, ui.errors), (1, 1, 1))

    def test_rich_live_view_handles_messages_without_markup(self):
        class TTY(io.StringIO):
            def isatty(self):
                return True
        stream = TTY()
        with TemporaryDirectory() as tmp:
            with patch.dict(os.environ, {"TERM": "xterm", "NO_COLOR": "", "LIVECLIP_PLAIN": ""}):
                with patch("liveclip.terminal_ui.shutil.get_terminal_size", return_value=os.terminal_size((90, 25))):
                    ui = SessionUI("record", Path(tmp), stream=stream, clock=lambda: 5.0)
                    ui.start()
                    ui.event("error", "[bold red] test\\x1b[31m")
                    ui.close()
        self.assertIn("finished with errors", stream.getvalue())
        self.assertEqual(ui.errors, 1)

    def test_bounded_control_character_output_and_duration(self):
        self.assertEqual(_elapsed(65), "01:05")
        self.assertEqual(_elapsed(3600), "01:00:00")
        self.assertNotIn("\n", _clip_message("stream\n status"))
        self.assertNotIn("\x1b", _clip_message("\x1b[31m malicious"))
        self.assertLessEqual(len(_clip_message("x" * 500)), 80)
        self.assertEqual(main(["bad"]), 2)

    def test_launcher_still_opens_desktop_and_does_not_depend_on_where(self):
        launcher = (Path(__file__).resolve().parents[1] / "START_WINDOWS.bat").read_text()
        self.assertIn('.[neon]', launcher)
        self.assertIn('-m liveclip.gui', launcher)
        self.assertIn('ffmpeg -version', launcher)
        self.assertNotIn('where ffmpeg', launcher)


if __name__ == "__main__":
    unittest.main()
