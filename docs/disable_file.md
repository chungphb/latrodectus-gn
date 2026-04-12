# disable_file

Prevents a BUILD.gn file from being loaded and parsed.

## Overview

`disable_file` allows you to completely skip loading a BUILD.gn file. Unlike `disable_target`, which still parses the file but makes targets no-op, `disable_file` prevents the file from being parsed at all.

This is useful when:
- The BUILD.gn file contains `declare_args()` that conflict with your project
- The file has top-level `assert()` statements that fail
- You want to completely exclude a directory without any parsing overhead

## Usage

```gn
disable_file(file_path)
```

### Parameters

- `file_path`: The full path to the BUILD.gn file starting with `//` (e.g., `"//foo/bar/BUILD.gn"`)

### Example

```gn
# In //latrodectus/updates.gni
disable_file("//third_party/unwanted/BUILD.gn")
```

When GN attempts to load `//third_party/unwanted/BUILD.gn`, it will be skipped entirely.

## How It Works

1. `disable_file()` registers the file path to be skipped
2. When the loader attempts to load the file, it checks the disabled files list
3. If the file is disabled, the loader skips execution and returns immediately
4. No targets from the file are defined (the file is effectively empty)

## Important Notes

### vs disable_target

| Feature | disable_file | disable_target |
|---------|-------------|----------------|
| Prevents file parsing | Yes | No |
| Avoids declare_args conflicts | Yes | No |
| Avoids top-level asserts | Yes | No |
| Target still exists (empty) | No | Yes |
| Can depend on disabled target | No | No (error) |

Use `disable_file` when you need to prevent a file from being parsed entirely.
Use `disable_target` when you only need to make specific targets no-op.

### Order Matters

Register `disable_file` **before** the file is loaded:

```gn
# Correct: disable first (usually in BUILDCONFIG.gn or early import)
disable_file("//foo/BUILD.gn")
# ... later, something tries to load //foo:target

# Wrong: file already loaded
import("//foo/BUILD.gn")  # Already parsed
disable_file("//foo/BUILD.gn")  # Too late!
```

### Use Full Paths

Always use full paths with `//` and include `BUILD.gn`:

```gn
# Correct
disable_file("//foo/bar/BUILD.gn")

# Wrong - missing BUILD.gn
disable_file("//foo/bar")

# Wrong - relative path
disable_file("bar/BUILD.gn")
```

### Error for Non-Existent Files

If you disable a file that doesn't exist or is never loaded, you'll get an error:

```
ERROR at //BUILD.gn:1:1: Unused disable_file.
disable_file("//foo/nonexistent/BUILD.gn")
^-----------
You set disable_file for the path "//foo/nonexistent/BUILD.gn" here but it was never matched.
```

### Dependencies on Disabled Files

If a target depends on something from a disabled file, you'll get an error since no targets are defined in disabled files:

```
ERROR: Can't load //disabled/BUILD.gn: Unable to find target
```

## Testing

```bash
# Build latrodectus-gn
npm run build

# Generate test project
./out/gn gen test_project/out --root=test_project

# Verify disabled file is skipped (with verbose logging)
./out/gn gen test_project/out --root=test_project -v
# Look for: "Skipping disabled file //path/to/BUILD.gn"
```

## Use Cases

### Avoiding declare_args Conflicts

```gn
# The original file has conflicting declare_args
# disable_file("//upstream/feature/BUILD.gn")

# Your replacement with different args
declare_args() {
  my_feature_enabled = true
}
```

### Excluding Problematic Directories

```gn
# Skip entire directory that causes build issues
disable_file("//third_party/broken/BUILD.gn")
```

### Platform-Specific Exclusions

```gn
if (is_latrodectus) {
  # Skip files that don't work with our build
  disable_file("//chrome/browser/feature/BUILD.gn")
}
```
