# chromium_src Override Mechanism

The `chromium_src/` directory provides a way to override or extend GN source files without modifying the upstream GN repository directly. This pattern is inspired by Brave Browser's chromium_src approach.

## Directory Structure

```
latrodectus-gn/
├── gn/                     # Upstream GN (submodule)
│   └── src/
│       └── <path>/
│           ├── foo.h
│           ├── foo.cc
│           └── ...
├── chromium_src/           # Our overrides (mirrors src/ structure)
│   └── <path>/
│       ├── foo.h           # Header override
│       ├── foo.cc          # Source override
│       └── latrodectus_bar.cc   # New source file
└── patches/                # Minimal patches for hooks
```

## How It Works

### 1. Include Path Priority

The build system adds `chromium_src/` to the include path with **highest priority**:

```
-I../chromium_src -I../gn/src -I.
```

When code does `#include "<path>/foo.h"`, it finds `chromium_src/<path>/foo.h` first (if it exists).

### 2. Source File Override

For `.cc` files, `build/gen.py` replaces the original source with the chromium_src version:

```
Original: src/<path>/foo.cc
Override: chromium_src/<path>/foo.cc
```

The override file typically uses the **include-and-extend** pattern.

### 3. Object File Location

Object files are generated inside `out/`, keeping the source tree clean:

```
out/chromium_src/<path>/foo.o    # Override objects
out/src/<path>/bar.o             # Original file objects
```

## Override Patterns

### Pattern 1: Include and Extend (Recommended)

Include the original file, then add new code:

```cpp
// chromium_src/<path>/foo.cc

// Include the original implementation
#include "../../gn/src/<path>/foo.cc"

// Add new code in the same namespace
namespace original_namespace {

void MyNewFunction() {
  // New functionality
}

}  // namespace original_namespace
```

### Pattern 2: Header Override

Override a header to add declarations:

```cpp
// chromium_src/<path>/foo.h

#ifndef LATRODECTUS_PATH_FOO_H_
#define LATRODECTUS_PATH_FOO_H_

// Include the original header
#include "../../gn/src/<path>/foo.h"

// Add new declarations
namespace original_namespace {

void MyNewFunction();
bool MyNewHelper(int arg);

}  // namespace original_namespace

#endif
```

### Pattern 3: New Source Files

Add completely new source files (prefix with `latrodectus_`):

```cpp
// chromium_src/<path>/latrodectus_feature.cc

#include "<path>/foo.h"  // Can include original headers

namespace original_namespace {

void LatrodectusSpecificFeature() {
  // Implementation
}

}  // namespace original_namespace
```

## File Detection Rules

| File Pattern | Behavior |
|--------------|----------|
| `chromium_src/<path>/foo.cc` | Replaces `src/<path>/foo.cc` in build |
| `chromium_src/<path>/foo.h` | Found first via include path |
| `chromium_src/<path>/latrodectus_*.cc` | Added as new source file |

## When to Use Each Approach

### Use chromium_src for:
- Adding new functions or classes
- Large blocks of new code
- Include-and-extend patterns
- New standalone source files

### Use patches for:
- Modifying class definitions (adding members)
- Inserting code inside existing functions
- Small changes that can't use include-and-extend

## Complete Example

### Adding a new feature to an existing module

**Step 1: Create header override**

```cpp
// chromium_src/gn/feature.h

#ifndef LATRODECTUS_GN_FEATURE_H_
#define LATRODECTUS_GN_FEATURE_H_

#include "../../gn/src/gn/feature.h"

namespace feature {

// New declaration
bool IsLatrodectusFeatureEnabled();

}  // namespace feature

#endif
```

**Step 2: Create source override**

```cpp
// chromium_src/gn/feature.cc

// Include original implementation
#include "../../gn/src/gn/feature.cc"

namespace feature {

// New implementation
bool IsLatrodectusFeatureEnabled() {
  return true;
}

}  // namespace feature
```

**Step 3: Build**

```bash
npm run build
```

The build system will:
1. Detect the override files
2. Replace `src/gn/feature.cc` with `chromium_src/gn/feature.cc`
3. Use `chromium_src/gn/feature.h` for includes (via path priority)
4. Generate object files in `out/chromium_src/gn/`

## Debugging

Check what overrides are detected during build:

```bash
npm run build
# Output shows:
# Applying chromium_src modifications:
#   Override: src/gn/foo.cc -> chromium_src/gn/foo.cc
```

Verify include paths in generated ninja:

```bash
grep "includes = " out/build.ninja | head -1
# Shows: includes = -I../chromium_src -I../gn/src -I.
```
