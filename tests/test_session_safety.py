"""Synthetic configuration tests; never disconnect a live RDP session."""
import importlib.util
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('session_safety', ROOT/'linux/session_safety.py')
safety = importlib.util.module_from_spec(spec); spec.loader.exec_module(safety)


class SessionSafetyTests(unittest.TestCase):
    def test_apply_is_idempotent_and_only_reloads_systemd_metadata(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); commands = []
            def run(argv, **kwargs): commands.append(argv)
            self.assertFalse(all(safety.check(root).values()))
            result = safety.apply(root, run)
            self.assertFalse(result['services_restarted'])
            self.assertTrue(all(safety.check(root).values()))
            self.assertEqual(commands, [['systemctl','daemon-reload']])
            self.assertEqual(safety.apply(root,run)['changed'], [])
            self.assertEqual(len(commands),1)

    def test_existing_managed_files_are_backed_up_and_other_configuration_preserved(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            existing = root / safety.NEEDRESTART
            existing.parent.mkdir(parents=True); existing.write_text('previous policy\n'); existing.chmod(0o640)
            distro = root/'etc/needrestart/needrestart.conf'; distro.write_text('distro defaults\n')
            result = safety.apply(root, lambda *a,**k: None)
            self.assertEqual((Path(result['backup'])/safety.NEEDRESTART).read_text(), 'previous policy\n')
            self.assertEqual(distro.read_text(),'distro defaults\n')

    def test_failed_daemon_reload_rolls_back_both_files(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); target = root/safety.NEEDRESTART
            target.parent.mkdir(parents=True); target.write_text('old config\n'); target.chmod(0o640)
            calls = []
            def run(argv, **kwargs):
                calls.append(argv)
                if kwargs['check']: raise subprocess.CalledProcessError(1,argv)
            with self.assertRaises(subprocess.CalledProcessError): safety.apply(root,run)
            self.assertEqual(target.read_text(),'old config\n')
            self.assertEqual(target.stat().st_mode & 0o777,0o640)
            self.assertFalse((root/safety.RELOAD).exists())
            self.assertEqual(len(calls),2)

    def test_managed_symlink_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name); outside = root/'outside'; outside.write_text('preserve')
            target = root/safety.NEEDRESTART; target.parent.mkdir(parents=True); target.symlink_to(outside)
            with self.assertRaises(ValueError): safety.apply(root, lambda *a,**k: None)
            self.assertEqual(outside.read_text(),'preserve')

    @unittest.skipUnless(shutil.which('perl'), 'Perl required for real needrestart policy evaluation')
    def test_real_perl_selection_excludes_only_rdp_and_retains_existing_defaults(self):
        script = r'''our %nrconf = (override_rc => { qr(^dbus\.service$) => 0, qr(^ssh\.service$) => 1 });
''' + safety.NEEDRESTART_TEXT + r'''
for my $unit (qw(xrdp.service xrdp-sesman.service ssh.service dbus.service other.service xrdp-other.service)) {
 my $selection=1;
 for my $pattern (keys %{$nrconf{override_rc}}) { $selection=$nrconf{override_rc}{$pattern} if $unit =~ /$pattern/; }
 print "$unit=$selection\n";
}
'''
        result = subprocess.run(['perl','-e',script],text=True,capture_output=True,check=True,timeout=5)
        self.assertEqual(result.stdout.splitlines(), ['xrdp.service=0','xrdp-sesman.service=0','ssh.service=1','dbus.service=0','other.service=1','xrdp-other.service=1'])


if __name__ == '__main__': unittest.main()
