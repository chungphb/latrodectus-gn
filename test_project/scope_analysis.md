# How update_target Works

## The Key Idea

`update_target` lets you modify a target's variables **after** it runs, without editing the original code.

```gn
# Register update BEFORE target
update_target("//:basic") {
  deps += [ ":helper" ]
}

# Target runs, then update is applied
group("basic") {
  deps = []
}

# Final result: deps = [":helper"]
```

---

## Example 1: Basic Update

### BUILD.gn
```gn
update_target("//:basic") {
  deps += [ ":helper" ]
}

group("basic") {
  deps = []
}
```

### What Happens Step by Step

**Step 1: `update_target` is called**
```
Block { deps += [":helper"] } is SAVED, not executed.

SAVED DATA:
  "//:basic" → { block: { deps += [":helper"] } }
```

**Step 2: `group("basic")` runs**
```
TARGET SCOPE created:
  deps = []
  target_name = "basic"
```

**Step 3: Update is applied**
```
1. Create EXTRA SCOPE (child of TARGET SCOPE)
   - Can read deps from parent → Gets []

2. Create BLOCK SCOPE (child of EXTRA SCOPE)
   - Execute: deps += [":helper"]
   - Read deps from parent chain → []
   - Compute: [] + [":helper"] = [":helper"]
   - Write: deps = [":helper"]

3. Merge BLOCK SCOPE back to TARGET SCOPE
   - TARGET SCOPE now has: deps = [":helper"]
```

**Final Result:**
```
deps = [":helper"]
```

---

## Example 2: Append to Existing Values

### BUILD.gn
```gn
update_target("//:append") {
  sources += [ "extra.cc" ]
}

source_set("append") {
  sources = [ "main.cc" ]
}
```

### What Happens

**Step 1: Target runs**
```
TARGET SCOPE:
  sources = ["main.cc"]
```

**Step 2: Update is applied**
```
1. Create EXTRA SCOPE (child of TARGET SCOPE)
   - Can read sources from parent → Gets ["main.cc"]

2. Create BLOCK SCOPE (child of EXTRA SCOPE)
   - Execute: sources += ["extra.cc"]
   - Read sources from parent chain → ["main.cc"]
   - Compute: ["main.cc"] + ["extra.cc"]
   - Write: sources = ["main.cc", "extra.cc"]

3. Merge BLOCK SCOPE back to TARGET SCOPE
   - TARGET SCOPE now has: sources = ["main.cc", "extra.cc"]
```

---

## Example 3: Multiple Updates

### BUILD.gn
```gn
update_target("//:multi") {
  deps += [ ":helper" ]
}

update_target("//:multi") {
  defines = [ "UPDATED=1" ]
}

source_set("multi") {
  sources = []
  deps = []
}
```

### What Happens

**After target runs:**
```
TARGET SCOPE:
  sources = []
  deps = []
```

**First update applied:**
```
1. Create EXTRA SCOPE (child of TARGET SCOPE)
   - Can read deps from parent → Gets []

2. Create BLOCK SCOPE (child of EXTRA SCOPE)
   - Execute: deps += [":helper"]
   - Read deps from parent chain → []
   - Compute: [] + [":helper"] = [":helper"]
   - Write: deps = [":helper"]

3. Merge BLOCK SCOPE back to TARGET SCOPE
   - TARGET SCOPE now has: deps = [":helper"]
```

**Second update applied:**
```
1. Create EXTRA SCOPE (child of TARGET SCOPE)
   - Can read deps from parent → Gets [":helper"]

2. Create BLOCK SCOPE (child of EXTRA SCOPE)
   - Execute: defines = ["UPDATED=1"]
   - Write: defines = ["UPDATED=1"]

3. Merge BLOCK SCOPE back to TARGET SCOPE
   - TARGET SCOPE now has: deps = [":helper"], defines = ["UPDATED=1"]
```

---

## 3 Scopes Explained

### The 3 Runtime Scopes

When an update runs, there are 3 scopes:

```
TARGET SCOPE          ← The actual target (has deps, sources, etc.)
  │
  └── EXTRA SCOPE     ← Bridge: target vars + SAVED SCOPE vars merged in
        │
        └── BLOCK SCOPE   ← Where update code runs (isolated writes)
```

### SAVED SCOPE

When `update_target()` is called, it saves a snapshot of the current scope:

```gn
# In //latrodectus/updates.gni
latrodectus_extra_dep = "//latrodectus:core"

update_target("//base:base") {
  deps += [ latrodectus_extra_dep ]  # Needs latrodectus_extra_dep from SAVED SCOPE
}
```

The SAVED SCOPE captures `latrodectus_extra_dep` so it's available later when the update runs.

### Why EXTRA SCOPE?

EXTRA SCOPE bridges TWO contexts:
1. **TARGET SCOPE** (via parent chain) → Read target's current `deps`, `sources`, etc.
2. **SAVED SCOPE** (via merge) → Read variables like `latrodectus_extra_dep` from registration time

```
BLOCK SCOPE reads deps → EXTRA → TARGET → Found!
BLOCK SCOPE reads latrodectus_extra_dep → EXTRA → Found! (merged from SAVED)
```

Without EXTRA SCOPE, the update block couldn't access registration-time variables.

| Scope | Why It Exists |
|-------|---------------|
| SAVED SCOPE | Captured when `update_target()` called. Holds context variables. |
| TARGET SCOPE | The real target being modified. |
| EXTRA SCOPE | Bridge that combines TARGET + SAVED for reading. |
| BLOCK SCOPE | Isolates WRITES so we can merge them cleanly. |

**The flow:**
1. SAVED SCOPE vars merged into EXTRA SCOPE
2. Update block READS through parent chain (BLOCK → EXTRA → TARGET)
3. Update block WRITES to BLOCK SCOPE
4. BLOCK SCOPE is merged back to TARGET SCOPE

---

## Testing

```bash
# From project root
npm run build
./out/gn gen test_project/out --root=test_project

# Test 1: Basic update
./out/gn desc test_project/out //:basic deps --root=test_project
# Expected: //:helper

# Test 2: Multiple updates
./out/gn desc test_project/out //:multi deps --root=test_project
./out/gn desc test_project/out //:multi defines --root=test_project
# Expected: //:helper
# Expected: UPDATED=1

# Test 3: Append to existing
./out/gn desc test_project/out //:append sources --root=test_project
# Expected: main.cc, extra.cc

# Test 4: Template instance
./out/gn desc test_project/out //:from_template deps --root=test_project
# Expected: //:helper
```

---

## Common Mistakes

### Wrong: Update AFTER target
```gn
group("foo") { deps = [] }           # Target runs first
update_target("//:foo") { ... }      # Update registered too late!
# WARNING: Unused update_target update
```

### Right: Update BEFORE target
```gn
update_target("//:foo") { ... }      # Register first
group("foo") { deps = [] }           # Target runs, update applied
```

### Wrong: Wrong label
```gn
update_target("//wrong:label") { ... }   # Typo in label
group("foo") { ... }                     # Never matches
# WARNING: Unused update_target update
```
