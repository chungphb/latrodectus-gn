# update_target Mechanism

The `update_target` and `update_template_instance` functions allow modifying targets after they are defined, without editing the original BUILD.gn files.

## Overview

This mechanism is adapted from [Vivaldi's GN fork](https://github.com/vivaldi/Vivaldi-GN) and enables:

- Adding dependencies to existing targets
- Adding sources to existing targets
- Modifying target properties

## Functions

### update_target

Modifies a target after its definition.

```gn
update_target("//path:target_name") {
  # Modifications applied after target is defined
  deps += [ "//my:dependency" ]
  sources += [ "//my/file.cc" ]
}
```

### update_template_instance

Modifies a template instantiation after it's invoked.

```gn
update_template_instance("//path:instance_name") {
  # Modifications applied after template is invoked
  deps += [ "//my:dependency" ]
}
```

## Usage Rules

### 1. Define updates BEFORE targets

Updates must be registered before the target is defined:

```gn
# Correct order
update_target("//:foo") { deps += [ ":bar" ] }
group("foo") { deps = [] }  # Update is applied here

# Wrong order - update won't be applied
group("foo") { deps = [] }
update_target("//:foo") { deps += [ ":bar" ] }  # Warning: unused
```

### 2. Use full target labels

```gn
update_target("//:target")           # Root target
update_target("//foo:bar")           # Target in //foo/BUILD.gn
update_target("//foo/bar:baz")       # Target in //foo/bar/BUILD.gn
```

### 3. Recommended: Use .gni files

Place updates in `.gni` files imported by the top-level BUILD.gn:

```gn
# //latrodectus/updates.gni
update_target("//base:base") {
  sources += [ "//latrodectus/base/latrodectus_feature.cc" ]
}

# //BUILD.gn
import("//latrodectus/updates.gni")
# ... rest of build
```

## Example

### BUILD.gn

```gn
source_set("helper") {
  sources = [ "helper.cc" ]
}

# Register update before target definition
update_target("//:my_app") {
  deps += [ ":helper" ]
}

# Target definition - update is applied automatically
executable("my_app") {
  sources = [ "main.cc" ]
  deps = []
}
```

### Result

The `my_app` target will have `:helper` in its deps, as if it was written:

```gn
executable("my_app") {
  sources = [ "main.cc" ]
  deps = [ ":helper" ]
}
```

## Template Instance Example

```gn
# Define a template
template("my_component") {
  source_set(target_name) {
    forward_variables_from(invoker, "*")
  }
}

# Register update for template instance
update_template_instance("//foo:bar") {
  defines += [ "LATRODECTUS_FEATURE=1" ]
}

# Use template - update is applied
my_component("bar") {
  sources = [ "bar.cc" ]
}
```

## Advanced Usage

### Multiple Updates for the Same Target

You can register multiple `update_target()` calls for the same target. They are applied in order:

```gn
update_target("//:foo") {
  deps += [ ":dep1" ]
}

update_target("//:foo") {
  deps += [ ":dep2" ]
}

group("foo") {
  deps = []
}
# Result: deps = [ ":dep1", ":dep2" ]
```

### Toolchain Handling

When building for multiple toolchains, the same target definition runs multiple times. The `update_target` mechanism uses a `targets_done` set to prevent applying updates multiple times:

```
//:my_target                      ← default toolchain (update applied)
//:my_target(//toolchain:arm64)   ← cross-compile (update skipped)
```

This ensures consistent behavior and prevents duplicate entries in lists.

## How It Works Internally

1. **Registration**: `update_target()` stores the update block in a static map (block is NOT executed yet)
2. **Deferred Execution**: The block and a scope snapshot are stored for later
3. **Application**: When `ExecuteGenericTarget()` runs, it calls `UpdateTheTarget()`
4. **Merge**: The update block executes in a temporary scope, then merges into the target's scope
5. **Deduplication**: `targets_done` prevents re-applying for multiple toolchains
6. **Verification**: At build end, `VerifyAllUpdatesUsed()` warns about unused updates

## Warnings

### Unused update warning

If an update doesn't match any target:

```
WARNING: Unused update_target update.
You set update_target updates of the label "//foo:bar" here and it was unused.
```

This usually means:
- The target label is wrong
- The target is defined before the update
- The target doesn't exist

## Testing

A test project is available at `test_project/`:

```bash
cd test_project
../out/gn gen out --root=.
../out/gn desc out //:my_target deps      # Shows :helper was added
../out/gn desc out //:templated deps      # Shows :helper was added
```
