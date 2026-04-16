#!/usr/bin/env python3
"""Base class for GN integration tests."""

import os
import shutil
import subprocess
import tempfile
import unittest


class GnTestCase(unittest.TestCase):
    """Base class for GN integration tests.

    Each test gets a fresh temporary directory with a minimal GN project setup.
    Tests can write BUILD.gn, updates.gni, etc. and run gn gen to verify behavior.
    """

    GN_BINARY = None  # Set by runner or auto-detected
    SHOW_NINJA = False  # Set by runner
    SHOW_GN_OUTPUT = False  # Set by runner

    def setUp(self):
        """Create temp directory with minimal GN project for each test."""
        self.temp_dir = tempfile.mkdtemp(prefix='gn_test_')
        self.root_dir = self.temp_dir
        self.out_dir = os.path.join(self.temp_dir, 'out')
        os.makedirs(self.out_dir)

        # Create minimal .gn file
        self.write_file('.gn', 'buildconfig = "//BUILDCONFIG.gn"')

        # Create minimal BUILDCONFIG.gn with default toolchain
        self.write_file('BUILDCONFIG.gn', 'set_default_toolchain("//toolchain:default")')

        # Create minimal toolchain
        self.write_file('toolchain/BUILD.gn', '''
toolchain("default") {
  tool("stamp") {
    command = "touch {{output}}"
    description = "STAMP {{output}}"
  }
  tool("copy") {
    command = "cp {{source}} {{output}}"
    description = "COPY {{source}} {{output}}"
  }
  tool("cxx") {
    command = "c++ -c {{source}} -o {{output}}"
    description = "CXX {{source}}"
    outputs = ["{{source_out_dir}}/{{label_name}}.{{source_name_part}}.o"]
  }
  tool("link") {
    command = "c++ {{inputs}} -o {{output}}"
    description = "LINK {{output}}"
    outputs = ["{{root_out_dir}}/{{target_output_name}}"]
  }
  tool("alink") {
    command = "ar rcs {{output}} {{inputs}}"
    description = "AR {{output}}"
    outputs = ["{{target_out_dir}}/{{target_output_name}}.a"]
  }
}
''')

    def tearDown(self):
        """Clean up temp directory, optionally showing ninja files first."""
        if self.SHOW_NINJA:
            self._print_ninja_files()
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    SEPARATOR = '----------------------------------------'

    def _print_ninja_files(self):
        """Print all ninja files in out/ and out/obj/."""
        # Print main build.ninja
        build_ninja = os.path.join(self.out_dir, 'build.ninja')
        if os.path.exists(build_ninja):
            print(f"\nbuild.ninja\n{self.SEPARATOR}")
            with open(build_ninja) as fp:
                print(fp.read())

        # Print target ninja files
        obj_dir = os.path.join(self.out_dir, 'obj')
        if not os.path.exists(obj_dir):
            return
        for root, dirs, files in os.walk(obj_dir):
            for f in files:
                if f.endswith('.ninja'):
                    path = os.path.join(root, f)
                    rel_path = os.path.relpath(path, obj_dir)
                    print(f"\n{rel_path}\n{self.SEPARATOR}")
                    with open(path) as fp:
                        print(fp.read())

    # ========== File Helpers ==========

    def write_file(self, path, content):
        """Write content to a file relative to root_dir."""
        full_path = os.path.join(self.root_dir, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, 'w') as f:
            f.write(content.strip() + '\n')

    def read_file(self, path):
        """Read a file relative to root_dir."""
        full_path = os.path.join(self.root_dir, path)
        with open(full_path, 'r') as f:
            return f.read()

    def file_exists(self, path):
        """Check if file exists relative to root_dir."""
        return os.path.exists(os.path.join(self.root_dir, path))

    # ========== GN Execution ==========

    def run_gn_gen(self, args=None, expect_success=True):
        """Run gn gen and return (success, stdout, stderr)."""
        cmd = [self.GN_BINARY, 'gen', self.out_dir, '--root=' + self.root_dir]
        if args:
            cmd.extend(args)

        result = subprocess.run(cmd, capture_output=True, text=True)
        success = result.returncode == 0

        if self.SHOW_GN_OUTPUT:
            print(f"\ngn gen output\n{self.SEPARATOR}")
            print(f"Command: {' '.join(cmd)}")
            print(f"Return code: {result.returncode}")
            if result.stdout:
                print(f"STDOUT:\n{result.stdout}")
            if result.stderr:
                print(f"STDERR:\n{result.stderr}")

        if expect_success and not success:
            self.fail(f"gn gen failed:\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")

        return success, result.stdout, result.stderr

    # ========== Ninja Output Helpers ==========

    def read_ninja_file(self, name):
        """Read a ninja file from out/obj/."""
        path = os.path.join(self.out_dir, 'obj', name)
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        return None

    def read_build_ninja(self):
        """Read the main build.ninja file."""
        path = os.path.join(self.out_dir, 'build.ninja')
        if os.path.exists(path):
            with open(path, 'r') as f:
                return f.read()
        return None

    # ========== Assertion Helpers ==========

    def assertNinjaContains(self, ninja_file, text, msg=None):
        """Assert ninja file contains text."""
        content = self.read_ninja_file(ninja_file)
        if content is None:
            self.fail(msg or f"Ninja file {ninja_file} does not exist")
        if text not in content:
            self.fail(msg or f"Expected '{text}' in {ninja_file}, got:\n{content}")

    def assertNinjaNotContains(self, ninja_file, text, msg=None):
        """Assert ninja file does NOT contain text."""
        content = self.read_ninja_file(ninja_file)
        if content is not None and text in content:
            self.fail(msg or f"Did not expect '{text}' in {ninja_file}, got:\n{content}")

    def assertNinjaFileExists(self, ninja_file, msg=None):
        """Assert ninja file exists."""
        content = self.read_ninja_file(ninja_file)
        if content is None:
            self.fail(msg or f"Ninja file {ninja_file} does not exist")

    def assertNinjaFileNotExists(self, ninja_file, msg=None):
        """Assert ninja file does NOT exist."""
        content = self.read_ninja_file(ninja_file)
        if content is not None:
            self.fail(msg or f"Ninja file {ninja_file} should not exist but it does")

    def assertGnGenFails(self, error_substring=None):
        """Assert that gn gen fails, optionally with specific error."""
        success, stdout, stderr = self.run_gn_gen(expect_success=False)
        self.assertFalse(success, "Expected gn gen to fail but it succeeded")
        if error_substring:
            combined = stdout + stderr
            self.assertIn(error_substring, combined,
                f"Expected error containing '{error_substring}', got:\n{combined}")
        return stderr

    def assertGnGenSucceeds(self):
        """Assert that gn gen succeeds."""
        success, stdout, stderr = self.run_gn_gen(expect_success=True)
        self.assertTrue(success, f"Expected gn gen to succeed but it failed:\n{stderr}")
        return stdout, stderr

    def assertGnGenSucceedsWithWarning(self, warning_substring):
        """Assert that gn gen succeeds but emits a specific warning."""
        success, stdout, stderr = self.run_gn_gen(expect_success=True)
        self.assertTrue(success, f"Expected gn gen to succeed but it failed:\n{stderr}")
        combined = stdout + stderr
        self.assertIn(warning_substring, combined,
            f"Expected warning containing '{warning_substring}', got:\n{combined}")
        return stdout, stderr
