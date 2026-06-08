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
1. Create EXTRA SCOPE (child of SAVED SCOPE)
   - Merge TARGET SCOPE vars → Gets deps = []

2. Create BLOCK SCOPE (child of EXTRA SCOPE)
   - Execute: deps += [":helper"]
   - Read deps from EXTRA SCOPE → []
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
1. Create EXTRA SCOPE (child of SAVED SCOPE)
   - Merge TARGET SCOPE vars → Gets sources = ["main.cc"]

2. Create BLOCK SCOPE (child of EXTRA SCOPE)
   - Execute: sources += ["extra.cc"]
   - Read sources from EXTRA SCOPE → ["main.cc"]
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
1. Create EXTRA SCOPE (child of SAVED SCOPE)
   - Merge TARGET SCOPE vars → Gets deps = []

2. Create BLOCK SCOPE (child of EXTRA SCOPE)
   - Execute: deps += [":helper"]
   - Read deps from EXTRA SCOPE → []
   - Compute: [] + [":helper"] = [":helper"]
   - Write: deps = [":helper"]

3. Merge BLOCK SCOPE back to TARGET SCOPE
   - TARGET SCOPE now has: deps = [":helper"]
```

**Second update applied:**
```
1. Create EXTRA SCOPE (child of SAVED SCOPE)
   - Merge TARGET SCOPE vars → Gets deps = [":helper"]

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
SAVED SCOPE           ← Captured when update_target() called (has config vars)
  │
  └── EXTRA SCOPE     ← Bridge: SAVED context via parent + TARGET vars merged in
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
1. **SAVED SCOPE** (via parent chain) → Read variables like `latrodectus_extra_dep` from registration time
2. **TARGET SCOPE** (via merge) → Read target's current `deps`, `sources`, etc.

```
BLOCK SCOPE reads latrodectus_extra_dep → EXTRA → SAVED → Found! (via parent chain)
BLOCK SCOPE reads deps → EXTRA → Found! (merged from TARGET)
```

Without EXTRA SCOPE, the update block couldn't access registration-time variables (like imported config flags).

| Scope | Why It Exists |
|-------|---------------|
| SAVED SCOPE | Captured when `update_target()` called. Holds context variables (imports, config flags). |
| TARGET SCOPE | The real target being modified. |
| EXTRA SCOPE | Child of SAVED (parent chain access) + TARGET vars merged in. |
| BLOCK SCOPE | Isolates WRITES so we can merge them cleanly. |

**The flow:**
1. EXTRA SCOPE created as child of SAVED SCOPE (parent chain gives access to registration context)
2. TARGET SCOPE vars merged into EXTRA SCOPE (target vars take precedence)
3. Update block READS through parent chain (BLOCK → EXTRA → SAVED) or from merged TARGET vars
4. Update block WRITES to BLOCK SCOPE
5. BLOCK SCOPE is merged back to TARGET SCOPE

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
