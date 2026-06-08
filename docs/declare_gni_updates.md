# declare_gni_updates

Declares a `.gni` file containing `update_gni_file` calls for automatic import ordering.

## Overview

`declare_gni_updates` solves the ordering problem where `update_gni_file()` must be called before the target `.gni` file is imported. By declaring the updater file early (typically in `BUILDCONFIG.gn`), the system ensures updates are applied regardless of import order elsewhere.

## Usage

```gn
declare_gni_updates(updater_file_path)
```

### Parameters

- `updater_file_path`: The full path to a `.gni` file containing `update_gni_file()` calls, starting with `//`

### Example

```gn
# In BUILDCONFIG.gn (runs early)
declare_gni_updates("//latrodectus/feature_updates.gni")

# feature_updates.gni contains:
update_gni_file("//build/config/features.gni") {
  enable_feature = true
}

# Later, in any BUILD.gn:
import("//build/config/features.gni")  # Updates applied automatically!
```

## How It Works

### 1. Scanning Phase

When `declare_gni_updates("//latrodectus/updates.gni")` is called:

1. GN loads and parses the updater file into an AST (Abstract Syntax Tree)
2. The AST is walked to find all `update_gni_file()` calls
3. For each call, the target file path is extracted
4. A mapping is registered: `target_file → updater_file`

### 2. Import Phase

When any file calls `import("//target.gni")`:

1. GN checks if there's a registered updater for `//target.gni`
2. If found, the updater file is automatically imported first
3. This executes the `update_gni_file()` calls before the target is imported
4. The target file is then imported with updates already registered

```
BUILDCONFIG.gn: declare_gni_updates("//updates.gni")
  └─> Scans updates.gni, finds: update_gni_file("//config.gni")
  └─> Registers mapping: //config.gni → //updates.gni

BUILD.gn: import("//config.gni")
  └─> Checks mappings, finds //updates.gni
  └─> Auto-imports //updates.gni first (registers update)
  └─> Imports //config.gni (update applied)
```

## AST Traversal Details

The `ExtractUpdateGniFileTargets` function walks the parsed AST to find `update_gni_file()` calls. Understanding this helps explain what patterns are supported.

### How GN Code Becomes an AST

When GN parses a file like:

```gn
update_gni_file("//foo.gni") {
  x = 1
}

if (condition) {
  update_gni_file("//bar.gni") {
    y = 2
  }
}
```

It creates a tree structure:

```
BlockNode (root - the whole file)
├── FunctionCallNode ("update_gni_file")
│   ├── ListNode (args)
│   │   └── LiteralNode ("//foo.gni")
│   └── BlockNode (body)
└── ConditionNode (if)
    └── BlockNode (if body)
        └── FunctionCallNode ("update_gni_file")
            ├── ListNode (args)
            │   └── LiteralNode ("//bar.gni")
            └── BlockNode (body)
```

### Node Types and Traversal

| Node Type | What It Represents | Recursion Logic |
|-----------|-------------------|-----------------|
| `BlockNode` | A `{ ... }` block containing statements | Visit each statement, plus the `End()` node |
| `FunctionCallNode` | A call like `foo(args) { block }` | Check if it's `update_gni_file`, then visit args and block |
| `ListNode` | Arguments list `(a, b, c)` | Visit each item in the list |
| `ConditionNode` | An `if/else` statement | Visit both `if_true()` and `if_false()` branches |

### Supported Patterns

The AST traversal finds `update_gni_file()` calls in these locations:

**Top-level calls:**
```gn
update_gni_file("//config.gni") { ... }
```

**Inside if/else blocks:**
```gn
if (is_linux) {
  update_gni_file("//linux_config.gni") { ... }
} else if (is_mac) {
  update_gni_file("//mac_config.gni") { ... }
} else {
  update_gni_file("//default_config.gni") { ... }
}
```

**Inside foreach loops:**
```gn
foreach(file, gni_files) {
  # Note: Only literal strings are extracted, not variables
  update_gni_file("//static_path.gni") { ... }
}
```

**Nested in other function blocks:**
```gn
template("my_template") {
  update_gni_file("//template_config.gni") { ... }
}
```

### Limitations

1. **Static analysis only**: The AST is scanned without execution, so:
   - Variable references are not resolved: `update_gni_file(my_var)` won't be found
   - Only literal string arguments work: `update_gni_file("//literal.gni")`

2. **Conditional paths not evaluated**: If you have:
   ```gn
   if (is_linux) {
     update_gni_file("//linux.gni") { ... }
   }
   ```
   The `//linux.gni` mapping is registered regardless of the `is_linux` value. This is usually fine because the `update_gni_file()` call itself will be conditionally executed when the updater file is imported.

3. **No escape sequence handling**: File paths with escape sequences are extracted as-is (though this is rarely needed for paths).

## Important Notes

### Place in BUILDCONFIG.gn

`declare_gni_updates()` should be called early, ideally in `BUILDCONFIG.gn`, to ensure mappings are registered before any imports:

```gn
# BUILDCONFIG.gn
declare_gni_updates("//latrodectus/updates.gni")
set_default_toolchain("//toolchain:default")
```

### Use Full Paths

Always use full paths with `//`:

```gn
# Correct
declare_gni_updates("//latrodectus/updates.gni")

# Wrong - will produce an error
declare_gni_updates("latrodectus/updates.gni")
```

### Only .gni Files

The updater file must be a `.gni` file:

```gn
# Correct
declare_gni_updates("//latrodectus/updates.gni")

# Wrong - will produce an error
declare_gni_updates("//latrodectus/updates.txt")
```

## Testing

```bash
# Build latrodectus-gn
npm run build

# Run tests
npm test

# Run specific declare_gni_updates tests
python3 tests/run_tests.py -v test_declare_gni_updates
```