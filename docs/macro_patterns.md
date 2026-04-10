# Chromium_src Macro Patterns

## Pattern 1: Skip the Next Statement

Use when you need to skip/replace whatever statement follows (a line, if block, for loop, etc).

```cpp
#define MACRO \
  new_code(); \
  if (false)

MACRO
old_statement;  // Skipped
```

## Pattern 2: Replace an If Condition

Use when you need to change the condition of an existing if statement.

```cpp
#define MACRO \
  }           \
  if (new_expr) {

if (old_expr) {
  MACRO
  <code>
}
```

## Pattern 3: Hijack Identifier in Header

Use when you need to inject declarations into a header file without patching.

**For variables** (ends with `;`):
```cpp
#define some_var \
  some_var;      \
  int injected_field = 0

// Original: Type some_var;
// Expands:  Type some_var; int injected_field = 0;
```

**For functions** (ends with `()`):
```cpp
#define SomeFunc       \
  SomeFunc();          \
  void InjectedFunc(); \
  void SomeFunc_Unused

// Original: void SomeFunc();
// Expands:  void SomeFunc(); void InjectedFunc(); void SomeFunc_Unused();
```

Choose unique identifiers that won't collide with other code.

**Header guards**: chromium_src headers need their own guards (use file path):
```cpp
#ifndef LATRODECTUS_CHROMIUM_SRC_GN_SCOPE_H_
#define LATRODECTUS_CHROMIUM_SRC_GN_SCOPE_H_

// macros and #include here

#endif  // LATRODECTUS_CHROMIUM_SRC_GN_SCOPE_H_
```

## Guidelines

1. **Minimal patches**: Patches only add the macro hook. Logic goes in chromium_src.
2. **No guards**: If the macro isn't defined, the build should fail.
3. **Naming**: `LATRODECTUS_GN_<FILE>_<FUNCTION>` for patch macros; use original identifier names for header hijacks.
4. **Comments**: Each macro should explain what it does.
