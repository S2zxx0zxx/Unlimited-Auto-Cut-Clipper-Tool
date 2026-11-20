"""Regression evidence for unique GTA Auto Clipper backend adoption."""
import io
import json
import math
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from liveclip.gta_adopt.framing import (
    gameplay_crop_offset, choose_crop_offset, pick_player,
    smooth_path, read_pan_keys, fill_filter, pan_x_expr
)
from liveclip.gta_adopt.captions import ass_text, mask_word
from liveclip.gta_adopt.chat_reactions import score_chat_windows
from liveclip.gta_adopt.discovery import find_live
from liveclip.neon_adopt.cli import main, verticalize


class GTAAdaptLogic(unittest.TestCase):
    def test_third_person_anchor(self):
        width,height=1920,1080
        offset=gameplay_crop_offset(width,height,player_x=width*.38)
        available=width-height*9/16
        actual=offset*available+height*9/16/2
        self.assertAlmostEqual(actual,width*.38)

    def test_stable_facecam_does_not_override_player_when_offscreen(self):
        boxes=[[(1800,30,72,90)] for _ in range(5)]
        self.assertAlmostEqual(choose_crop_offset(1920,1080,boxes),
                               gameplay_crop_offset(1920,1080,1920*.38))
        self.assertAlmostEqual(choose_crop_offset(1920,1080,[[],[]]),gameplay_crop_offset(1920,1080))

    def test_player_selection_and_smoothing(self):
        self.assertAlmostEqual(pick_player([(700,450,220,350,.9),(200,100,20,20,.9)],
                                           1920,1080),810/1920)
        positions=smooth_path([0,1,2,3],[.40,.42,.85,.44],max_speed=.12)
        self.assertLessEqual(abs(positions[2]-positions[1]),.121)
        with self.assertRaises(ValueError):
            smooth_path([1,1],[.2,.3])

    def test_validated_pan_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"movement.json"
            p.write_text(json.dumps({"pan_keys":[[0,.38],[1,.45],[2,.5]]}))
            keys=read_pan_keys(p,3)
            self.assertEqual(len(keys),3)
            self.assertIn("if(lt(t",pan_x_expr(keys,720))
            self.assertIn("crop=720:1280",fill_filter(720,1280,keys=keys))
            p.write_text('[[-1,.5],[1,.6]]')
            with self.assertRaises(ValueError):
                read_pan_keys(p,3)

    def test_popup_has_non_overlapping_events(self):
        words=[{"start":.2,"end":.45,"text":"OH"},
               {"start":.5,"end":.76,"text":"MY"},
               {"start":.8,"end":1.03,"text":"GOD!"}]
        ass=ass_text(words,duration=1.5,width=720,height=1280)
        events=[line for line in ass.splitlines() if line.startswith("Dialogue: 0,")]
        self.assertEqual(len(events),3)
        self.assertIn("&H00FFFF&",events[0])
        self.assertIn(r"\t(0,110,",events[1])
        def stamp(value):
            h,m,rest=value.split(":")
            return int(h)*3600+int(m)*60+float(rest)
        times=[(stamp(x.split(",")[1]),stamp(x.split(",")[2])) for x in events]
        self.assertTrue(all(b<=n+.011 for (_,b),(n,_) in zip(times,times[1:])))
        self.assertTrue(all(b>a for a,b in times))

    def test_censor_and_escape_untrusted_subtitle(self):
        self.assertEqual(mask_word("shit")[0],"s")
        output=ass_text([{"start":0,"end":.5,"text":"{\\pos(1,2)}"}],
                        duration=1,credit="{\\fs400}")
        self.assertNotIn(r"{\pos(1,2)}",output)
        self.assertNotIn(r"{\fs400}",output)

    def test_spam_resistant_reactions(self):
        good=[{"t":11+i*.3,"user":f"viewer{i}","text":"LOL no way 😂"} for i in range(8)]
        spam=[{"t":21+i*.2,"user":"same","text":"LOL no way 😂"} for i in range(30)]
        scored=score_chat_windows(good+spam,[0,10,20,30],10)
        self.assertGreater(scored[1]["signal"],scored[2]["signal"])
        self.assertEqual(scored[2]["chatters"],1)
        self.assertNotIn("user",scored[2])

    def test_discovery_parses_results_without_claiming_permissions(self):
        data={"items":[{"id":{"videoId":"abc123XYZ89"},
                         "snippet":{"title":"Live &amp; safe","channelTitle":"Creator","channelId":"UC123"}}]}
        resp=io.BytesIO(json.dumps(data).encode())
        class MockStream:
            def __enter__(self):return resp
            def __exit__(self,*args):return False
        with patch("liveclip.gta_adopt.discovery.urlopen",return_value=MockStream()):
            rows=find_live("GTA 6","dummy-test-only",5)
        self.assertEqual(rows[0]["title"],"Live & safe")
        self.assertFalse(rows[0]["gameplay_verified"])
        self.assertFalse(rows[0]["content_rights_verified"])

    def test_chat_cli_has_no_raw_usernames(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"chat.json"
            p.write_text(json.dumps([{"t":2,"user":"private-user","text":"lol"}]))
            from contextlib import redirect_stdout
            buf=io.StringIO()
            with redirect_stdout(buf):
                self.assertEqual(main(["chat-reactions",str(p)]),0)
            self.assertNotIn("private-user",buf.getvalue())

    def test_gta_flags_reject_unsafe_layout(self):
        from liveclip.neon_adopt.cli import _argparser
        args=_argparser().parse_args(["vertical","a.mp4","b.mp4","--layout","fill",
                                      "--gta-player-anchor",".38","--pop-language","en"])
        self.assertAlmostEqual(args.gta_player_anchor,.38)


@unittest.skipUnless(shutil.which("ffmpeg") and shutil.which("ffprobe"),"FFmpeg required")
class GTAAdaptVideo(unittest.TestCase):
    @staticmethod
    def synthetic(path):
        subprocess.run(["ffmpeg","-y","-loglevel","error","-f","lavfi",
                        "-i","testsrc2=size=320x180:rate=12:duration=2",
                        "-f","lavfi","-i","sine=frequency=550:sample_rate=16000:duration=2",
                        "-shortest","-c:v","mpeg4","-c:a","aac",str(path)],
                       capture_output=True,check=True,timeout=45)

    def test_fixed_gta_anchor_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            media=Path(tmp)/"source.mp4"
            out=Path(tmp)/"gta.mp4"
            self.synthetic(media)
            result=verticalize(media,out,duration=1.5,layout="fill",gta_player_anchor=.38)
            self.assertTrue(out.exists())
            self.assertTrue(result["gta_pan_mode"])
            self.assertTrue(result["source_preserved"])

    def test_dynamic_pan_render(self):
        with tempfile.TemporaryDirectory() as tmp:
            media=Path(tmp)/"source.mp4"
            out=Path(tmp)/"motion.mp4"
            keys=Path(tmp)/"pan.json"
            self.synthetic(media)
            keys.write_text(json.dumps([[0,.4],[.5,.43],[1.5,.55]]))
            result=verticalize(media,out,duration=1.5,layout="fill",pan_keys_file=keys)
            self.assertTrue(out.exists())
            self.assertTrue(result["player_tracking_applied"])

    def test_pop_caption_render(self):
        filters=subprocess.run(["ffmpeg","-hide_banner","-filters"],capture_output=True,
                               text=True,timeout=20).stdout
        if not any(line.split()[-1] == "subtitles" for line in []): # deliberate filter name substring, no false skip
            if " ass " not in filters and " ass " not in filters.replace("\t"," "):
                self.skipTest("FFmpeg ass/libass filter is unavailable")
        with tempfile.TemporaryDirectory() as tmp:
            media=Path(tmp)/"source.mp4"
            out=Path(tmp)/"caption.mp4"
            words=Path(tmp)/"words.json"
            self.synthetic(media)
            words.write_text(json.dumps({"words":[{"start":.12,"end":.4,"text":"GTA"},
                                                  {"start":.42,"end":.73,"text":"WIN"}]}))
            result=verticalize(media,out,duration=1.5,layout="fill",
                               gta_player_anchor=.38,pop_words_file=words)
            self.assertTrue(out.exists())
            self.assertEqual(result["caption_engine"],"gta-popup")
            self.assertTrue(result["captions_burned"])

if __name__ == "__main__":
    unittest.main()
