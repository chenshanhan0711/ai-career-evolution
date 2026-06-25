import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.config import DATABASE_NAME, get_database_path, resolve_database_path


class DatabasePathTests(unittest.TestCase):
    def test_macos_and_windows_use_project_root(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            for system_name in ["Darwin", "Windows"]:
                path = resolve_database_path(
                    system_name=system_name,
                    environ={},
                    project_root=root,
                )
                self.assertEqual(path, (root / DATABASE_NAME).resolve())

    def test_linux_uses_var_lib_by_default(self):
        path = resolve_database_path(system_name="Linux", environ={})
        self.assertEqual(path, Path("/var/lib/ai-career-viz/ai_career.db"))

    def test_linux_respects_xdg_data_home(self):
        path = resolve_database_path(
            system_name="Linux",
            environ={"XDG_DATA_HOME": "/srv/app-data"},
        )
        self.assertEqual(path, Path("/srv/app-data/ai-career-viz/ai_career.db"))

    def test_explicit_path_has_highest_priority(self):
        path = resolve_database_path(
            system_name="Linux",
            environ={"APP_DB_PATH": "/data/custom.db"},
        )
        self.assertEqual(path, Path("/data/custom.db"))

    def test_unwritable_linux_path_falls_back_to_user_data(self):
        with (
            patch(
                "src.config.resolve_database_path",
                return_value=Path("/var/lib/ai-career-viz/ai_career.db"),
            ),
            patch("src.config.Path.mkdir"),
            patch("src.config.os.access", return_value=False),
            patch("src.config.Path.home", return_value=Path("/tmp/test-home")),
        ):
            path = get_database_path()

        self.assertEqual(
            path,
            Path("/tmp/test-home/.local/share/ai-career-viz/ai_career.db"),
        )


if __name__ == "__main__":
    unittest.main()
