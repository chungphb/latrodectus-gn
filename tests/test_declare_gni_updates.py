#!/usr/bin/env python3
"""Tests for declare_gni_updates functionality.

declare_gni_updates solves the ordering problem where update_gni_file() must be
called before the target .gni file is imported. It scans a file for
update_gni_file() calls and registers mappings so that when the target files
are imported, the updater file is automatically imported first.
"""

from textwrap import dedent
from gn_test_base import GnTestCase


class DeclareGniUpdatesBasicTest(GnTestCase):
    """Basic tests for declare_gni_updates functionality."""

    def test_auto_imports_updater_before_target(self):
        """declare_gni_updates auto-imports updater file before target is imported."""
        # In BUILDCONFIG.gn, we declare the updater
        self.write_file('BUILD.gn', dedent('''
            # Note: BUILDCONFIG.gn declares the updater
            # When we import config.gni, updates.gni is auto-imported first
            import("//config.gni")
            assert(feature_enabled, "feature should be enabled by auto-imported updater")
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

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()

    def test_works_with_any_import_order(self):
        """Target file can be imported anywhere without requiring manual ordering."""
        # The key benefit: no need to manually import updates.gni before config.gni
        self.write_file('BUILD.gn', dedent('''
            # Direct import of config.gni without importing updates.gni
            import("//config.gni")
            assert(my_value == "updated", "value should be updated")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            my_value = "original"
        '''))

        self.write_file('updates.gni', dedent('''
            update_gni_file("//config.gni") {
              my_value = "updated"
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()

    def test_multiple_targets_in_same_updater(self):
        """Updater file with multiple update_gni_file calls works correctly."""
        self.write_file('BUILD.gn', dedent('''
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

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()


class DeclareGniUpdatesMultipleImportersTest(GnTestCase):
    """Tests for multiple BUILD.gn files importing the same target."""

    def test_multiple_importers_all_see_updates(self):
        """All importers see the updated values regardless of import order."""
        self.write_file('BUILD.gn', dedent('''
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

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()


class DeclareGniUpdatesValidationTest(GnTestCase):
    """Tests for declare_gni_updates input validation."""

    def test_missing_path_prefix(self):
        """declare_gni_updates without // prefix fails with clear error."""
        self.write_file('BUILD.gn', dedent('''
            group("main") {}
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenFails("declare_gni_updates requires a full path starting with //")

    def test_non_gni_file_rejected(self):
        """declare_gni_updates on non-.gni file fails with clear error."""
        self.write_file('BUILD.gn', dedent('''
            group("main") {}
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.txt")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenFails("declare_gni_updates requires a .gni file path")

    def test_nonexistent_updater_file_fails(self):
        """declare_gni_updates on nonexistent file fails with clear error."""
        self.write_file('BUILD.gn', dedent('''
            group("main") {}
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//nonexistent.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        # Nonexistent file should fail - it's a configuration error
        self.assertGnGenFails("Unable to load")


class DeclareGniUpdatesSubdirTest(GnTestCase):
    """Tests for declare_gni_updates with files in subdirectories."""

    def test_updater_in_subdirectory(self):
        """Updater file in subdirectory works correctly."""
        self.write_file('BUILD.gn', dedent('''
            import("//build/config.gni")
            assert(setting == "custom", "setting should be customized")
            group("main") {}
        '''))

        self.write_file('build/config.gni', dedent('''
            setting = "default"
        '''))

        self.write_file('latrodectus/updates.gni', dedent('''
            update_gni_file("//build/config.gni") {
              setting = "custom"
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//latrodectus/updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()


class DeclareGniUpdatesNestedCallsTest(GnTestCase):
    """Tests for update_gni_file calls nested inside control structures.

    The declare_gni_updates function uses AST traversal to find update_gni_file
    calls. These tests verify that calls nested inside if blocks, foreach loops,
    and other structures are correctly extracted.
    """

    def test_finds_update_inside_if_block(self):
        """update_gni_file inside an if block is found by AST traversal."""
        self.write_file('BUILD.gn', dedent('''
            import("//config.gni")
            assert(feature_enabled, "feature should be enabled")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            feature_enabled = false
        '''))

        # The update_gni_file is inside an if block
        self.write_file('updates.gni', dedent('''
            is_latrodectus = true
            if (is_latrodectus) {
              update_gni_file("//config.gni") {
                feature_enabled = true
              }
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()

    def test_finds_update_inside_else_block(self):
        """update_gni_file inside an else block is found by AST traversal."""
        self.write_file('BUILD.gn', dedent('''
            import("//config.gni")
            assert(value == "from_else", "value should come from else block")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            value = "original"
        '''))

        # The update_gni_file is inside an else block
        self.write_file('updates.gni', dedent('''
            condition = false
            if (condition) {
              # This won't execute
            } else {
              update_gni_file("//config.gni") {
                value = "from_else"
              }
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()

    def test_finds_update_inside_foreach_loop(self):
        """update_gni_file inside a foreach loop is found by AST traversal."""
        self.write_file('BUILD.gn', dedent('''
            import("//config.gni")
            assert(loop_value == "updated", "value should be updated from foreach")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            loop_value = "original"
        '''))

        # The update_gni_file is inside a foreach loop
        self.write_file('updates.gni', dedent('''
            items = ["a", "b"]
            foreach(item, items) {
              update_gni_file("//config.gni") {
                loop_value = "updated"
              }
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()

    def test_finds_update_nested_multiple_levels(self):
        """update_gni_file nested multiple levels deep is found."""
        self.write_file('BUILD.gn', dedent('''
            import("//config.gni")
            assert(deep_value == "deep_updated", "deeply nested update should work")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            deep_value = "original"
        '''))

        # The update_gni_file is nested inside if > foreach > if
        self.write_file('updates.gni', dedent('''
            outer_condition = true
            items = ["x"]
            if (outer_condition) {
              foreach(item, items) {
                inner_condition = true
                if (inner_condition) {
                  update_gni_file("//config.gni") {
                    deep_value = "deep_updated"
                  }
                }
              }
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()

    def test_finds_multiple_updates_in_different_branches(self):
        """Multiple update_gni_file calls in different if/else branches are all found."""
        self.write_file('BUILD.gn', dedent('''
            import("//config1.gni")
            import("//config2.gni")
            assert(val1 == "updated1", "val1 should be updated")
            assert(val2 == "updated2", "val2 should be updated")
            group("main") {}
        '''))

        self.write_file('config1.gni', dedent('''
            val1 = "original1"
        '''))

        self.write_file('config2.gni', dedent('''
            val2 = "original2"
        '''))

        # Updates in both if and else branches - both should be found by AST
        self.write_file('updates.gni', dedent('''
            condition = true
            if (condition) {
              update_gni_file("//config1.gni") {
                val1 = "updated1"
              }
            } else {
              # This won't execute, but the path is still registered
            }

            # This one is always executed
            update_gni_file("//config2.gni") {
              val2 = "updated2"
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()

    def test_finds_update_inside_template_definition(self):
        """update_gni_file inside a template definition block is found."""
        self.write_file('BUILD.gn', dedent('''
            import("//config.gni")
            assert(template_value == "from_template", "value should be updated")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            template_value = "original"
        '''))

        # The update_gni_file is inside a template definition
        # Note: This is an unusual pattern, but tests AST traversal into function blocks
        self.write_file('updates.gni', dedent('''
            # This update is at top level and will execute
            update_gni_file("//config.gni") {
              template_value = "from_template"
            }

            # This template contains an update_gni_file - the AST traversal
            # will find it and register the mapping, even though the template
            # is never invoked
            template("unused_template") {
              update_gni_file("//other_config.gni") {
                unused_value = true
              }
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()


class DeclareGniUpdatesImportLoopTest(GnTestCase):
    """Tests for import loop detection with declare_gni_updates."""

    def test_detects_loop_when_target_imports_updater(self):
        """Detects loop when target file imports the updater file."""
        # config.gni imports updates.gni, updates.gni imports config.gni
        self.write_file('BUILD.gn', dedent('''
            import("//config.gni")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            import("//updates.gni")
            value = "original"
        '''))

        self.write_file('updates.gni', dedent('''
            import("//config.gni")
            update_gni_file("//config.gni") {
              value = "updated"
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenFails("import loop")

    def test_skips_update_when_updater_imports_target_first(self):
        """Skips update when updater's import chain imports target first."""
        # another_updates.gni imports updates.gni before calling update_gni_file,
        # updates.gni imports config.gni, so config.gni gets cached first.
        self.write_file('BUILD.gn', dedent('''
            import("//config.gni")
            assert(value == "original")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            value = "original"
        '''))

        self.write_file('updates.gni', dedent('''
            import("//config.gni")
        '''))

        self.write_file('another_updates.gni', dedent('''
            import("//updates.gni")
            update_gni_file("//config.gni") {
              value = "updated"
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//another_updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenSucceeds()

    def test_detects_loop_when_build_imports_updater_first(self):
        """Detects loop when BUILD.gn imports updater before target."""
        # BUILD.gn imports another_updates.gni first, which imports updates.gni,
        # which imports config.gni, triggering auto-import of another_updates.gni.
        self.write_file('BUILD.gn', dedent('''
            import("//another_updates.gni")
            import("//config.gni")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            value = "original"
        '''))

        self.write_file('updates.gni', dedent('''
            import("//config.gni")
        '''))

        self.write_file('another_updates.gni', dedent('''
            import("//updates.gni")
            update_gni_file("//config.gni") {
              value = "updated"
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//another_updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenFails("import loop")

    def test_detects_loop_when_build_imports_intermediate_file(self):
        """Detects loop when BUILD.gn imports file that triggers updater chain."""
        # BUILD.gn imports updates.gni, which imports config.gni,
        # triggering auto-import of another_updates.gni, which imports updates.gni.
        self.write_file('BUILD.gn', dedent('''
            import("//updates.gni")
            group("main") {}
        '''))

        self.write_file('config.gni', dedent('''
            value = "original"
        '''))

        self.write_file('updates.gni', dedent('''
            import("//config.gni")
        '''))

        self.write_file('another_updates.gni', dedent('''
            import("//updates.gni")
            update_gni_file("//config.gni") {
              value = "updated"
            }
        '''))

        self.write_file('BUILDCONFIG.gn', dedent('''
            declare_gni_updates("//another_updates.gni")
            set_default_toolchain("//toolchain:default")
        '''))

        self.assertGnGenFails("import loop")
