# disable_template_instance

Disables a template instantiation, creating an empty placeholder target.

## Overview

`disable_template_instance` allows you to disable targets created by templates without patching the original BUILD.gn file. When the template is invoked with the specified label, the template body is skipped and an empty placeholder group target is created instead. Note that other targets cannot depend on a disabled template instance - `gn gen` will fail with an error if this is detected.

## Usage

```gn
disable_template_instance(target_label)
```

### Parameters

- `target_label`: The full label of the template instantiation to disable (e.g., `"//foo:bar"`)
- Supports wildcard `*` to disable all template instances in a directory (e.g., `"//foo:*"`)

### Example

```gn
# In //latrodectus/updates.gni
disable_template_instance("//third_party/some_feature:templated_target")
```

When the template `templated_target` is invoked, it will be converted to an empty group target.

## How It Works

1. `disable_template_instance()` registers the target label to be disabled
2. When the template is invoked, the hook checks if it's in the disabled set
3. If disabled, the template body is skipped entirely
4. An empty placeholder group target is created with the same label
5. Dependencies on this placeholder are detected and produce an error

## Important Notes

### Use for Template-Created Targets

`disable_template_instance` is specifically for targets created by templates. For regular targets, use `disable_target` instead.

```gn
# For template invocations
template("my_template") {
  group(target_name) { ... }
}
my_template("foo") { }  # Use disable_template_instance

# For regular targets
source_set("bar") { }  # Use disable_target
```

### Order Matters

Register `disable_template_instance` **before** the template is invoked:

```gn
# Correct: disable first
disable_template_instance("//foo:bar")
# ... later, my_template("bar") is called

# Wrong: template already invoked
my_template("bar") { ... }  # Already ran
disable_template_instance("//foo:bar")  # Too late!
```

### Use Full Labels

Always use full labels with `//`:

```gn
# Correct
disable_template_instance("//foo:bar")

# Wrong - relative labels won't match
disable_template_instance(":bar")
```

### Error for Non-Existent Template Instances

If you disable a template instance that doesn't exist, you'll get an error:

```
ERROR at //BUILD.gn:1:1: Unused disable_template_instance.
disable_template_instance("//foo:nonexistent")
^------------------------
You set disable_template_instance for the label "//foo:nonexistent" here but it was never matched.
```

### Error for Dependencies on Disabled Template Instances

If another target depends on a disabled template instance, `gn gen` will fail with an error:

```
ERROR at //BUILD.gn:10:12: Dependency on disabled template instance.
  deps = [ ":disabled_template_target" ]
           ^--------------------------
Target //:my_target depends on disabled template instance //:disabled_template_target.
```

This prevents broken builds where a target expects its dependency to provide something, but the dependency has been disabled.

## Testing

```bash
# Build latrodectus-gn
npm run build

# Generate test project
./out/gn gen test_project/out --root=test_project

# Check disabled template instance exists as empty group
./out/gn desc test_project/out //:disabled_template_target deps --root=test_project
# Expected: (empty output)
```

## Use Cases

### Removing Unwanted Template-Based Features

```gn
# Disable a single template instance
disable_template_instance("//third_party/feature:unwanted_component")

# Disable all template instances in a directory
disable_template_instance("//third_party/unwanted_lib:*")
```

### Platform-Specific Exclusions

```gn
if (is_latrodectus) {
  disable_template_instance("//chrome/browser:some_chrome_template_target")
}
```

### Disabling Generated Targets

Many build systems use templates to generate multiple targets. `disable_template_instance` lets you selectively disable specific instantiations:

```gn
# Original in upstream code
foreach(name, [ "feature_a", "feature_b", "feature_c" ]) {
  my_component(name) { ... }
}

# In your updates.gni, disable just feature_b
disable_template_instance("//upstream:feature_b")
```
