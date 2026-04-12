# disable_target

Disables a target, making it a no-op with empty sources and deps.

## Overview

`disable_target` allows you to disable a target without patching the original BUILD.gn file. The target will still be defined (so dependencies don't fail), but it will have no sources, deps, or other properties.

## Usage

```gn
disable_target(target_label)
```

### Parameters

- `target_label`: The full label of the target to disable (e.g., `"//foo:bar"`)

### Example

```gn
# In //latrodectus/updates.gni
disable_target("//third_party/some_feature:some_target")
```

When `some_target` is defined, it will be converted to an empty target.

## How It Works

1. `disable_target()` registers the target label to be disabled
2. When the target is defined, the hook checks if it's in the disabled set
3. If disabled, all target variables are cleared (sources, deps, etc.)
4. The target is still generated, but as an empty no-op target

## Important Notes

### BUILD.gn is Still Parsed

`disable_target` does **not** prevent the BUILD.gn file from being loaded. If the BUILD.gn file contains top-level asserts or errors outside of target definitions, they will still execute.

```gn
# //some/BUILD.gn
import("//config.gni")
assert(some_condition)  # This WILL still run!

source_set("target") {
  # This will be disabled
}
```

### Order Matters

Register `disable_target` **before** the target is defined:

```gn
# Correct: disable first
disable_target("//foo:bar")
# ... later, foo:bar is defined

# Wrong: target already defined
source_set("bar") { ... }  # Already ran
disable_target("//foo:bar")  # Too late!
```

### Use Full Labels

Always use full labels with `//`:

```gn
# Correct
disable_target("//foo:bar")

# Wrong - relative labels won't match
disable_target(":bar")
```

### Warning for Non-Existent Targets

If you disable a target that doesn't exist, you'll get a warning:

```
WARNING at //BUILD.gn:1:1: Unused disable_target.
disable_target("//foo:nonexistent")
^-------------
You set disable_target for the label "//foo:nonexistent" here but it was never matched.
```

## Cleared Variables

When a target is disabled, these variables are cleared to empty lists:

- `sources`
- `deps`
- `public_deps`
- `data_deps`
- `inputs`
- `data`

## Testing

```bash
# Build latrodectus-gn
npm run build

# Generate test project
./out/gn gen test_project/out --root=test_project

# Check disabled target has no deps
./out/gn desc test_project/out //:disabled_target deps --root=test_project
# Expected: (empty output)
```

## Use Cases

### Removing Unwanted Features

```gn
# Disable a feature you don't want
disable_target("//third_party/feature:unwanted")
```

### Platform-Specific Exclusions

```gn
if (is_latrodectus) {
  disable_target("//chrome/browser:some_chrome_only_feature")
}
```

### Replacing with Custom Implementation

```gn
# Disable original, provide your own
disable_target("//base:original_impl")

# Your custom implementation can have the same public interface
source_set("custom_impl") {
  # ...
}
```
