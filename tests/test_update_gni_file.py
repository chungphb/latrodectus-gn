#!/usr/bin/env python3
"""Tests for update_gni_file functionality.

update_gni_file modifies variables in .gni files AFTER the file has been executed
but BEFORE the result is cached and returned to importers. This allows
overriding configuration variables defined in .gni files.

NOTE: update_gni_file only works on .gni files (loaded through import_manager),
not on BUILD.gn files. For modifying target properties like visibility,
use update_target instead.
"""

from textwrap import dedent
from gn_test_base import GnTestCase


class UpdateFileGniTest(GnTestCase):
    """Tests for update_gni_file on .gni files.

    This is the primary use case: modifying variables in .gni config files
    so that importing BUILD.gn files see the updated values.
    """

    def test_modifies_gni_variable_for_importers(self):
        """update_gni_file on .gni modifies variables seen by importers."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")
            # feature_enabled was false in config.gni but updated to true
            assert(feature_enabled, "feature should be enabled")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            feature_enabled = false
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              feature_enabled = true
            }
        '''))

        self.assertGnGenSucceeds()

    def test_appends_to_gni_list_for_importers(self):
        """update_gni_file can append to lists in .gni files."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")
            # extra_deps had one item, now has two
            assert(extra_deps == [":original", ":added"], "deps should include added")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            extra_deps = [":original"]
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              extra_deps += [":added"]
            }
        '''))

        self.assertGnGenSucceeds()

    def test_multiple_importers_see_updated_values(self):
        """Multiple BUILD.gn files importing the same .gni see updated values."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {
              deps = ["//dir1:target", "//dir2:target"]
            }
        '''))

        self.write_file('config.gni', dedent('''
            shared_value = "original"
        '''))

        self.write_file('dir1/BUILD.gn', dedent('''
            import("//config.gni")
            assert(shared_value == "updated", "dir1 should see updated value")
            group("target") {}
        '''))

        self.write_file('dir2/BUILD.gn', dedent('''
            import("//config.gni")
            assert(shared_value == "updated", "dir2 should see updated value")
            group("target") {}
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              shared_value = "updated"
            }
        '''))

        self.assertGnGenSucceeds()

    def test_sets_new_variable_in_gni(self):
        """update_gni_file can set a new variable in .gni file scope."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")
            assert(new_var == "created", "new_var should be created")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            existing_var = "original"
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              new_var = "created"
            }
        '''))

        self.assertGnGenSucceeds()


class UpdateFileMultipleGniTest(GnTestCase):
    """Tests for multiple update_gni_file calls on .gni files."""

    def test_multiple_updates_same_gni(self):
        """Multiple updates on same .gni file are applied in order."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")
            assert(my_list == ["first", "second"], "list should have both values")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            my_list = []
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              my_list += ["first"]
            }
            update_gni_file("//config.gni") {
              my_list += ["second"]
            }
        '''))

        self.assertGnGenSucceeds()

    def test_multiple_different_gni_files(self):
        """Can update multiple different .gni files."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config1.gni")
            import("//config2.gni")
            assert(var1 == "updated1", "var1 should be updated")
            assert(var2 == "updated2", "var2 should be updated")
            group("main") {}
        '''))

        self.write_file('config1.gni', dedent('''
            var1 = "original1"
        '''))

        self.write_file('config2.gni', dedent('''
            var2 = "original2"
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config1.gni") {
              var1 = "updated1"
            }
            update_gni_file("//config2.gni") {
              var2 = "updated2"
            }
        '''))

        self.assertGnGenSucceeds()


class UpdateFileRegistrationContextTest(GnTestCase):
    """Tests for registration context variable access in update_gni_file."""

    def test_accesses_imported_variables(self):
        """update_gni_file block can access variables from imports at registration time."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            import("//config.gni")
            assert(my_list == ["from_config"], "list should have value from config")
            group("main") {}
        '''))

        self.write_file('values.gni', dedent('''
            extra_value = "from_config"
        '''))

        self.write_file('config.gni', dedent('''
            my_list = []
        '''))

        self.write_file('updates.gni', dedent('''
            import("//values.gni")
            update_gni_file("//config.gni") {
              my_list += [extra_value]
            }
        '''))

        self.assertGnGenSucceeds()


class UpdateFileInputValidationTest(GnTestCase):
    """Tests for update_gni_file input validation."""

    def test_missing_path_prefix(self):
        """update_gni_file without // prefix fails with clear error."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("not_a_path") {
              visibility = []
            }
        '''))

        self.assertGnGenFails("update_gni_file requires a full path starting with //")

    def test_relative_path(self):
        """update_gni_file with relative path fails."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("subdir/config.gni") {
              visibility = []
            }
        '''))

        self.assertGnGenFails("update_gni_file requires a full path starting with //")

    def test_non_gni_file_rejected(self):
        """update_gni_file on non-.gni file fails with clear error."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//subdir/BUILD.gn") {
              visibility = []
            }
        '''))

        self.assertGnGenFails("update_gni_file requires a .gni file path")

    def test_nonexistent_gni_file(self):
        """update_gni_file on nonexistent .gni file succeeds with warning."""
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") { deps = [] }
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//nonexistent/config.gni") {
              my_var = "test"
            }
        '''))

        # Warns about unused update_gni_file but succeeds
        self.assertGnGenSucceedsWithWarning("update_gni_file")
