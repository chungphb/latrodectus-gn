#!/usr/bin/env python3
# Latrodectus GN build generator wrapper.
# Adds chromium_src override support to the upstream gen.py.
#
# chromium_src supports two patterns:
# 1. Override: chromium_src/gn/foo.cc replaces src/gn/foo.cc
# 2. Addition: chromium_src/gn/latrodectus_*.cc are added as new sources

import argparse
import os
import sys

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LATRODECTUS_ROOT = os.path.dirname(SCRIPT_DIR)
GN_ROOT = os.path.join(LATRODECTUS_ROOT, 'gn')
CHROMIUM_SRC = os.path.join(LATRODECTUS_ROOT, 'chromium_src')

# Add GN's build directory to path so we can import from it
sys.path.insert(0, os.path.join(GN_ROOT, 'build'))

# Change to GN_ROOT before importing so paths resolve correctly
os.chdir(GN_ROOT)

# Now import the upstream gen module
import gen as upstream_gen


def find_chromium_src_files():
    """
    Find all files in chromium_src:
    - Overrides: .cc/.h files that match existing src/ files
    - Additions: .cc files that start with 'latrodectus_' (new files to add)
    """
    overrides = {}
    additions = []

    if not os.path.isdir(CHROMIUM_SRC):
        return overrides, additions

    for root, dirs, files in os.walk(CHROMIUM_SRC):
        for f in files:
            file_path = os.path.join(root, f)
            rel_path = os.path.relpath(file_path, CHROMIUM_SRC)

            if f.endswith('.cc'):
                if f.startswith('latrodectus_'):
                    # This is a new file to add, not an override
                    additions.append(file_path)
                else:
                    # This is an override of an existing file
                    original_path = os.path.join('src', rel_path)
                    overrides[original_path] = file_path
            elif f.endswith('.h'):
                # Header overrides (handled via include path priority)
                original_path = os.path.join('src', rel_path)
                overrides[original_path] = file_path

    return overrides, additions


# Track chromium_src files for special handling in ninja generation
chromium_src_sources = {}  # maps "chromium_src/..." -> actual file path


def apply_overrides_to_sources(sources, overrides):
    """Replace original source paths with override paths where applicable."""
    new_sources = []
    for src in sources:
        if src in overrides:
            # Use chromium_src/... path (object goes to out/chromium_src/...)
            rel_from_chromium_src = os.path.relpath(overrides[src], CHROMIUM_SRC)
            chromium_src_path = os.path.join('chromium_src', rel_from_chromium_src)
            new_sources.append(chromium_src_path)
            # Track the actual file location
            chromium_src_sources[chromium_src_path] = overrides[src]
            print(f'  Override: {src} -> {chromium_src_path}')
        else:
            new_sources.append(src)
    return new_sources


def add_latrodectus_sources(sources, additions, target_dir='src/gn'):
    """Add Latrodectus-specific source files to the sources list."""
    for addition in additions:
        rel_from_chromium_src = os.path.relpath(addition, CHROMIUM_SRC)
        addition_target_dir = os.path.dirname(os.path.join('src', rel_from_chromium_src))

        # Only add to gn_lib (src/gn/) sources
        if addition_target_dir == target_dir:
            chromium_src_path = os.path.join('chromium_src', rel_from_chromium_src)
            sources.append(chromium_src_path)
            chromium_src_sources[chromium_src_path] = addition
            print(f'  Addition: {chromium_src_path}')

    return sources


# Store original WriteGNNinja
original_WriteGNNinja = upstream_gen.WriteGNNinja


def patched_WriteGNNinja(path, platform, host, options, args_list):
    """Patched WriteGNNinja that applies chromium_src overrides and additions."""
    global chromium_src_sources
    chromium_src_sources = {}  # Reset for each run

    overrides, additions = find_chromium_src_files()

    if overrides or additions:
        print('Applying chromium_src modifications:')

    # Patch WriteGenericNinja to modify sources and include paths
    original_WriteGenericNinja = upstream_gen.WriteGenericNinja

    def patched_WriteGenericNinja(path, static_libraries, executables,
                                   cxx, ar, ld, platform, host, options,
                                   args_list, cflags=[], ldflags=[],
                                   libflags=[], include_dirs=[], solibs=[]):
        # Add chromium_src to include_dirs with highest priority
        chromium_src_rel = os.path.relpath(CHROMIUM_SRC, os.path.dirname(path))
        new_include_dirs = [chromium_src_rel] + include_dirs

        # Apply source overrides and additions to gn_lib
        if 'gn_lib' in static_libraries:
            static_libraries['gn_lib']['sources'] = apply_overrides_to_sources(
                static_libraries['gn_lib']['sources'], overrides)
            static_libraries['gn_lib']['sources'] = add_latrodectus_sources(
                static_libraries['gn_lib']['sources'], additions, 'src/gn')

        # Apply source overrides to other libraries
        for lib_name, settings in static_libraries.items():
            if lib_name != 'gn_lib':
                settings['sources'] = apply_overrides_to_sources(
                    settings['sources'], overrides)

        # Apply source overrides to executables
        for exe_name, settings in executables.items():
            settings['sources'] = apply_overrides_to_sources(
                settings['sources'], overrides)

        # Call original, then fix chromium_src paths in the ninja file
        result = original_WriteGenericNinja(
            path, static_libraries, executables,
            cxx, ar, ld, platform, host, options,
            args_list, cflags, ldflags, libflags, new_include_dirs, solibs)

        # Post-process ninja file to fix chromium_src source paths
        if chromium_src_sources:
            with open(path, 'r') as f:
                content = f.read()

            out_dir = os.path.dirname(path)
            for src_path, actual_path in chromium_src_sources.items():
                # The upstream gen.py would have written:
                #   build chromium_src/gn/foo.o: cxx ../src/chromium_src/gn/foo.cc
                # We need to fix it to:
                #   build chromium_src/gn/foo.o: cxx ../../chromium_src/gn/foo.cc
                wrong_src = os.path.relpath(
                    os.path.join(GN_ROOT, src_path),
                    out_dir)
                correct_src = os.path.relpath(actual_path, out_dir)
                content = content.replace(f'cxx {wrong_src}', f'cxx {correct_src}')

            with open(path, 'w') as f:
                f.write(content)

        return result

    upstream_gen.WriteGenericNinja = patched_WriteGenericNinja

    return original_WriteGNNinja(path, platform, host, options, args_list)


# Monkey-patch
upstream_gen.WriteGNNinja = patched_WriteGNNinja


if __name__ == '__main__':
    sys.exit(upstream_gen.main(sys.argv[1:]))
