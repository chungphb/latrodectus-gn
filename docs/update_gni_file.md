# update_gni_file

Modifies variables in a `.gni` file before they are imported.

## Overview

`update_gni_file` allows you to override or modify variables defined in `.gni` files without patching them directly. The modifications are applied after the file is executed but before the result is cached, so all BUILD.gn files that import the `.gni` file see the updated values.

## Usage

```gn
update_gni_file(file_path) {
  # modifications to variables
}
```

### Parameters

- `file_path`: The full path to the `.gni` file starting with `//` (e.g., `"//build/config/features.gni"`)

### Example

```gn
# In //latrodectus/updates.gni
update_gni_file("//build/config/features.gni") {
  enable_feature_x = true
}

update_gni_file("//build/config/deps.gni") {
  extra_deps += [ "//latrodectus:my_component" ]
}
```

## How It Works

1. `update_gni_file()` registers the update block to be applied when the `.gni` file is imported
2. When any BUILD.gn imports the `.gni` file, GN executes the file first
3. The update block is then executed, modifying the scope variables
4. The modified scope is cached and returned to all importers
5. All BUILD.gn files that import the `.gni` see the same updated values

```
BUILD.gn #1: import("//config.gni")
  └─> First import: parse → execute → apply updates → cache
       └─> All subsequent imports reuse the cached (modified) result

BUILD.gn #2: import("//config.gni")
  └─> Uses cached result with modifications already applied

BUILD.gn #3: import("//config.gni")
  └─> Uses cached result with modifications already applied
```

## Important Notes

### Only Works on `.gni` Files

`update_gni_file` only works on `.gni` files loaded through `import()`. It does not work on BUILD.gn files. For modifying target properties, use `update_target` instead.

```gn
# Correct: .gni file
update_gni_file("//build/config.gni") { ... }

# Wrong: BUILD.gn file - will produce an error
update_gni_file("//foo/BUILD.gn") { ... }
```

### Order Matters

Register `update_gni_file` **before** the `.gni` file is imported:

```gn
# Correct: update registered first
import("//latrodectus/updates.gni")  # Contains update_gni_file calls
import("//build/config.gni")    # Sees updated values

# Wrong: config already imported
import("//build/config.gni")    # Original values cached
import("//latrodectus/updates.gni")  # Too late!
```

### Use Full Paths

Always use full paths with `//`:

```gn
# Correct
update_gni_file("//build/config/features.gni")

# Wrong - will produce an error
update_gni_file("config/features.gni")
```

### Error for Non-Existent Files

If you register an update for a `.gni` file that is never imported, you'll get an error:

```
ERROR at //BUILD.gn:1:1: Unused update_gni_file.
update_gni_file("//nonexistent/config.gni")
^-----------------------------------------
You set update_gni_file for the path "//nonexistent/config.gni" here but it was never matched.
```

### Multiple Updates

You can register multiple updates for the same file. They are applied in order:

```gn
update_gni_file("//config.gni") {
  my_list += ["first"]
}

update_gni_file("//config.gni") {
  my_list += ["second"]
}

# Result: my_list contains both "first" and "second"
```

## Testing

```bash
# Build latrodectus-gn
npm run build

# Run tests
npm test

# Run specific update_gni_file tests
python3 tests/run_tests.py -v test_update_gni_file
```

## Use Cases

### Enabling/Disabling Features

```gn
# Override feature flags defined in upstream .gni files
update_gni_file("//build/config/features.gni") {
  enable_nacl = false
  enable_widevine = false
  enable_hangout_services_extension = false
}
```

### Adding Dependencies

```gn
# Add extra dependencies to a list defined in .gni
update_gni_file("//build/config/browser_deps.gni") {
  browser_deps += [
    "//latrodectus/browser:latrodectus_features",
    "//latrodectus/components:latrodectus_components",
  ]
}
```

### Modifying Default Values

```gn
# Change default configurations
update_gni_file("//build/config/compiler.gni") {
  default_optimization_level = "2"
  enable_iterator_debugging = false
}
```

### Platform-Specific Overrides

```gn
if (is_latrodectus && is_linux) {
  update_gni_file("//build/config/linux.gni") {
    use_custom_allocator = true
  }
}
```

## Comparison with Other Functions

| Function | Purpose | Target |
|----------|---------|--------|
| `update_gni_file` | Modify variables in `.gni` files | `.gni` files only |
| `update_target` | Modify target properties | Targets in BUILD.gn |
| `update_template_instance` | Modify template instance parameters | Template invocations |
| `disable_file` | Skip loading a BUILD.gn file | BUILD.gn files |
| `disable_target` | Create empty placeholder target | Targets in BUILD.gn |
