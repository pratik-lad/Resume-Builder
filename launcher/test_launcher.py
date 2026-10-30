import tempfile
import unittest
import zipfile
import hashlib
from pathlib import Path
from threading import Event
from unittest.mock import Mock, patch

from launcher import launcher


class LauncherTests(unittest.TestCase):
    def make_launcher(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        root = Path(directory.name)
        with patch.object(launcher, "LOG_DIR", root / "logs"), patch.object(
            launcher, "LOG_FILE", root / "logs" / "launcher.log"
        ):
            instance = launcher.Launcher(lambda _: None, Event())
        self.addCleanup(instance.close)
        return instance

    def test_workflow_setup_detection(self):
        self.assertEqual(launcher.workflow_ids("one\n\ntwo\n"), {"one", "two"})
        self.assertTrue(launcher.needs_setup(set()))
        self.assertFalse(launcher.needs_setup({launcher.WORKFLOW_ID}))

    def test_copy_launcher_from_removable_media(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            source = base / "usb" / "ResumeOptimizerLauncher.exe"
            source.parent.mkdir()
            source.write_bytes(b"launcher binary")
            with patch.object(launcher.sys, "frozen", True, create=True), patch.object(
                launcher.sys, "executable", str(source)
            ), patch.object(launcher, "APP_DIR", base / "profile"):
                target = launcher.install_local_launcher()
            self.assertEqual(target.read_bytes(), b"launcher binary")

    def test_runtime_update_preserves_user_data(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            app_root = base / "app"
            bundles = [base / "first.zip", base / "second.zip"]
            for bundle, compose in zip(bundles, ("version: one", "version: two")):
                with zipfile.ZipFile(bundle, "w") as archive:
                    archive.writestr("docker-compose.yml", compose)
                    archive.writestr(".env.example", "OLLAMA_HOST=http://host.docker.internal:11434")
            instance = self.make_launcher()
            with patch.object(launcher, "APP_ROOT", app_root):
                with patch.object(launcher, "runtime_bundle_path", return_value=bundles[0]):
                    instance.install_runtime()
                (app_root / ".env").write_text("USER_SETTING=keep", encoding="utf-8")
                output = app_root / "data" / "runs" / "run-1" / "resume.docx"
                output.parent.mkdir(parents=True)
                output.write_bytes(b"generated resume")
                with patch.object(launcher, "runtime_bundle_path", return_value=bundles[1]):
                    instance.install_runtime()
                self.assertEqual((app_root / "docker-compose.yml").read_text(), "version: two")
                self.assertEqual((app_root / ".env").read_text(), "USER_SETTING=keep")
                self.assertEqual(output.read_bytes(), b"generated resume")

    def test_workflow_import_and_publish(self):
        instance = self.make_launcher()
        instance._workflow_lists = Mock(return_value=(set(), set()))
        instance._compose = Mock()
        instance.wait_for_setup.set()
        with patch.object(launcher.webbrowser, "open") as open_browser:
            instance._finish_workflow()
        calls = [call.args for call in instance._compose.call_args_list]
        self.assertTrue(any("import:workflow" in call for call in calls))
        self.assertTrue(any("publish:workflow" in call for call in calls))
        self.assertIn(("restart", "n8n"), calls)
        open_browser.assert_called_once_with(launcher.SETUP_URL)

    def test_port_conflict_reports_api(self):
        instance = self.make_launcher()
        instance._compose = Mock(return_value=Mock(returncode=0, stdout=""))
        with patch.object(launcher, "port_is_listening", return_value=True):
            with self.assertRaisesRegex(launcher.LauncherError, "Port 8001.*api"):
                instance._assert_ports_available()

    def test_gguf_download_checks_hash_and_recovers_corrupt_file(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.gguf"
            source.write_bytes(b"GGUF" + b"model" * 100)
            target = root / "models" / "model.gguf"
            digest = hashlib.sha256(source.read_bytes()).hexdigest()
            launcher.download_verified(source.as_uri(), target, digest, source.stat().st_size, lambda _: None)
            self.assertEqual(target.read_bytes(), source.read_bytes())
            target.write_bytes(b"broken")
            launcher.download_verified(source.as_uri(), target, digest, source.stat().st_size, lambda _: None)
            self.assertEqual(target.read_bytes(), source.read_bytes())

    def test_launcher_adds_native_connection_without_losing_settings(self):
        instance = self.make_launcher()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("NUM_CTX=8192\nMODEL_EXTRACT=qwen3.5:4b\n", encoding="utf-8")
            with patch.object(launcher, "APP_ROOT", root):
                key, context = instance._ensure_llm_env()
                key_again, context_again = instance._ensure_llm_env()
            self.assertEqual(context, 8192)
            self.assertEqual((key_again, context_again), (key, context))
            self.assertTrue(key)
            text = (root / ".env").read_text(encoding="utf-8")
            self.assertIn("MODEL_EXTRACT=qwen3.5:4b", text)
            self.assertIn("LLM_HOST=http://host.docker.internal:18081", text)
            self.assertEqual(text.count("LLM_API_KEY="), 1)

    def test_launcher_fills_blank_api_key_in_place(self):
        instance = self.make_launcher()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / ".env").write_text("NUM_CTX=8192\nLLM_API_KEY=\n", encoding="utf-8")
            with patch.object(launcher, "APP_ROOT", root):
                key, context = instance._ensure_llm_env()
            self.assertTrue(key)
            self.assertEqual(context, 8192)
            self.assertEqual((root / ".env").read_text(encoding="utf-8").count("LLM_API_KEY="), 1)

    def test_gpu_selection_prefers_nvidia(self):
        instance = self.make_launcher()
        instance._run = Mock(return_value=Mock(returncode=0, stdout=(
            "Available devices:\n  Vulkan0: Intel Graphics\n"
            "  Vulkan1: NVIDIA GeForce GTX 1650 (4096 MiB free)\n")))
        self.assertEqual(instance._gpu_device(Path("llama-server.exe")), "Vulkan1")


if __name__ == "__main__":
    unittest.main()
