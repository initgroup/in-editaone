from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from backend.project_paths import relocated_project_path


class ProjectPathRelocationTests(unittest.TestCase):
    def test_missing_legacy_absolute_path_maps_to_existing_project_directory(self):
        with TemporaryDirectory() as temp:
            parent = Path(temp)
            root = parent / 'in-editaone'
            target = root / 'local-config'
            target.mkdir(parents=True)
            self.assertEqual(relocated_project_path(str(parent / 'data-editing-system/local-config'), root), target.resolve())
            self.assertIsNone(relocated_project_path(str(parent / 'another-project/local-config'), root))
            self.assertIsNone(relocated_project_path('local-config', root))

    def test_existing_paths_missing_targets_and_escape_paths_are_not_rewritten(self):
        with TemporaryDirectory() as temp:
            parent = Path(temp)
            root = parent / 'in-editaone'
            root.mkdir()
            legacy = parent / 'data-editing-system'
            legacy.mkdir()
            self.assertIsNone(relocated_project_path(str(legacy), root))
            self.assertIsNone(relocated_project_path(str(legacy / 'missing'), root))
            outside = parent / 'outside'
            outside.mkdir()
            self.assertIsNone(relocated_project_path(str(legacy / '../outside'), root))
