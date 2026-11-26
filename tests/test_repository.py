"""Local structural/regression tests, not claims of cloud deployment."""
import importlib.util
import json
import pathlib
import re
import tempfile
import tomllib
import unittest
from unittest.mock import patch

ROOT=pathlib.Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('configure_rdp',ROOT/'linux/configure_rdp.py')
config=importlib.util.module_from_spec(spec);spec.loader.exec_module(config)


class RepositoryTests(unittest.TestCase):
    def test_source_lock(self):
        lock=json.loads((ROOT/'config/sources.json').read_text())
        self.assertEqual(set(lock),{'xrdp','xorgxrdp'})
        for name,item in lock.items():
            self.assertTrue(item['url'].startswith('https://github.com/neutrinolabs/'+name+'/releases/download/'))
            self.assertRegex(item['sha256'],r'^[a-f0-9]{64}$')

    def test_clipboard_patch_has_expected_guards(self):
        text=(ROOT/'patches/xrdp-0.10.6.1-clipboard.patch').read_text()
        for item in ['g_selection_generation','clipboard_refuse_selection','megas_png_to_bmp','libpng >= 1.6','clip_msg_len']:
            self.assertIn(item,text)

    def test_config_only_global_listener(self):
        with tempfile.TemporaryDirectory() as folder:
            p=pathlib.Path(folder)
            conf=p/'etc/xrdp';conf.mkdir(parents=True)
            (conf/'xrdp.ini').write_text('[Globals]\nport=3389\nsecurity_layer=negotiate\ncertificate=\nkey_file=\nLogFile=xrdp.log\nautorun=\n#runtime_user=xrdp\n#runtime_group=xrdp\n[Xorg]\nport=-1\n')
            (conf/'sesman.ini').write_text('#SessionSockdirGroup=xrdp\nparam=Xorg\nparam=xrdp/xorg.conf\nLogFile=sesman.log\n')
            (conf/'gfx.toml').write_text('[x264.default]\nfps_num = 60\nthreads = 1\nvbv_max_bitrate = 0\nvbv_buffer_size = 0\n[x264.wan]\nvbv_max_bitrate = 15_000\n')
            x=p/'etc/X11/xrdp';x.mkdir(parents=True);(x/'xorg.conf').write_text('Section "Device"\nEndSection\n')
            with patch.object(config.shutil,'copy2'):
                config.configure(p)
                config.configure(p)
            ini=(conf/'xrdp.ini').read_text()
            self.assertIn('port=tcp://127.0.0.1:3389',ini)
            self.assertIn('port=-1',ini)
            self.assertEqual((x/'xorg.conf').read_text().count('ModulePath "/usr/lib/xorg/modules"'),1)
            gfx=tomllib.loads((conf/'gfx.toml').read_text())
            self.assertEqual(gfx['x264']['default']['vbv_max_bitrate'],20000)
            self.assertEqual(gfx['x264']['lan']['fps_num'],60)
            self.assertEqual(gfx['x264']['wan']['vbv_max_bitrate'],15000)
            self.assertEqual(gfx['x264']['default']['threads'],2)

    def test_graphics_profiles_are_scoped_and_idempotent(self):
        original = (
            '[codec]\norder = ["H.264", "RFX"]\nh264_encoder = "x264"\n'
            '[x264.default]\nfps_num = 30\npreset = "ultrafast"\n'
            'vbv_max_bitrate = 6000\nvbv_buffer_size = 600\n'
            '[x264.lan]\nvbv_max_bitrate = 6000\n'
            '[x264.wan]\nvbv_max_bitrate = 6000\n'
            '[x264.broadband_low]\npreset = "veryfast"\nvbv_max_bitrate = 1600\n'
            '[x264.modem]\nvbv_max_bitrate = 1200\n'
            '[OpenH264.default]\nTargetBitrate = 20000000\n'
        )
        updated = config.configure_gfx(original)
        self.assertEqual(config.configure_gfx(updated), updated)
        before, after = tomllib.loads(original), tomllib.loads(updated)
        self.assertEqual(before["codec"], after["codec"])
        self.assertEqual(before["OpenH264"], after["OpenH264"])
        for section in ("broadband_low", "modem"):
            self.assertEqual(before["x264"][section], after["x264"][section])
        for section in ("default", "lan", "wan"):
            self.assertEqual(after["x264"][section]["fps_num"], 60)
            self.assertEqual(after["x264"][section]["tune"], "zerolatency")
        self.assertEqual(after["x264"]["lan"]["vbv_max_bitrate"], 20000)
        self.assertEqual(after["x264"]["wan"]["vbv_max_bitrate"], 15000)

    def test_graphics_invalid_or_missing_config_fails_closed(self):
        for invalid in ("[x264.lan]\nfps_num=60\n",
                        "[x264.default]\nfps_num=30\nfps_num=60\n"):
            with self.assertRaises(ValueError):
                config.configure_gfx(invalid)

    def test_windows_history_is_opt_in(self):
        text=(ROOT/'windows/Rdp-ClipboardPng.ps1').read_text()
        self.assertTrue(text.startswith('param([switch]$EnableTextHistory)'))
        self.assertIn('if ($EnableTextHistory -and $textSource',text)
        history=(ROOT/'windows/Rdp-TextHistory.ps1').read_text()
        self.assertIn('ExcludeClipboardContentFromMonitorProcessing',history)
        self.assertIn("SetData('CanUploadToCloudClipboard',$false,$no)",history)

    def test_no_owner_specific_data(self):
        # No machine export was used as the repository payload. Broad secret
        # patterns supplement review; this is not a guarantee of secret absence.
        patterns=[r'AKIA[0-9A-Z]{16}',r'ASIA[0-9A-Z]{16}',r'-----BEGIN (?:RSA |OPENSSH |EC )?PRIVATE KEY-----',r'gh[pousr]_[A-Za-z0-9]{30,}',r'(?i)C:[\\/]Users[\\/][^\\/\s]+',r'i-[a-f0-9]{17}\b',r'\b\d{12}\b',r'[\w.+-]+@(?:gmail|outlook|hotmail)\.com']
        for path in ROOT.rglob('*'):
            if not path.is_file() or any(part in {'.git','.cache','__pycache__'} for part in path.relative_to(ROOT).parts): continue
            if path.name==pathlib.Path(__file__).name: continue
            text=path.read_text(encoding='utf-8')
            # Published upstream attribution is required by its license and is
            # not the installation owner's private contact information.
            if path.relative_to(ROOT).as_posix()=='licenses/xorgxrdp-X11.txt':
                text=text.replace('jay.sorg@gmail.com','upstream-author-contact')
            for pattern in patterns:
                self.assertIsNone(re.search(pattern,text),f'Private-data pattern in {path.relative_to(ROOT)}')


if __name__=='__main__': unittest.main()
