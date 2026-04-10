# Scope Analysis: How update_target Works

This document explains how **Scopes** work in the GN build system and how `update_target` leverages them to modify targets.

## What is a Scope?

A **Scope** is a container for variables during GN script execution. Scopes are **nested** (hierarchical):

- **Writing** goes into the current (top-level) scope
- **Reading** searches recursively through parent scopes until a match is found

```
┌─────────────────────────────┐
│  Build Config Scope         │  ← Global variables (host_cpu, etc.)
│  ┌───────────────────────┐  │
│  │  File Scope           │  │  ← Variables in BUILD.gn
│  │  ┌─────────────────┐  │  │
│  │  │  Block Scope    │  │  │  ← Variables inside a target/template
│  │  └─────────────────┘  │  │
│  └───────────────────────┘  │
└─────────────────────────────┘
```

## Step-by-Step: Scope Lifecycle in test_project

### Initial State: GN Starts Up

```
┌─────────────────────────────────────────────────────────┐
│  GLOBAL SCOPE (Build Config)                            │
│  ├── host_cpu = "x64"                                   │
│  ├── host_os = "mac"                                    │
│  ├── current_toolchain = "//toolchain:default"          │
│  └── ... (built-in variables)                           │
└─────────────────────────────────────────────────────────┘
```

GN creates a **global scope** with built-in variables. This is the root of all scopes.

---

### Step 1: Parse BUILDCONFIG.gn

```gn
set_default_toolchain("//toolchain:default")
```

```
┌─────────────────────────────────────────────────────────┐
│  GLOBAL SCOPE                                           │
│  ├── default_toolchain = "//toolchain:default"          │
│  └── ...                                                │
└─────────────────────────────────────────────────────────┘
```

The global scope is updated with the default toolchain.

---

### Step 2: Parse BUILD.gn - Line 1: `source_set("helper")`

GN creates a **new child scope** for this target:

```
┌─────────────────────────────────────────────────────────┐
│  GLOBAL SCOPE                                           │
│  │                                                      │
│  │  ┌─────────────────────────────────────────────┐     │
│  │  │  BLOCK SCOPE for source_set("helper")       │     │
│  │  │  ├── target_name = "helper"                 │     │
│  │  │  ├── sources = []                           │     │
│  │  │  └── (parent: GLOBAL SCOPE)                 │     │
│  │  └─────────────────────────────────────────────┘     │
│  │                                                      │
└─────────────────────────────────────────────────────────┘
```

**What happens internally:**

```cpp
// In ExecuteGenericTarget()
Scope block_scope(scope);  // Create child scope, parent = file scope
block_scope.SetValue("target_name", "helper");

// Execute the block { sources = [] }
block->Execute(&block_scope, err);  // Sets sources = [] in block_scope

// Target is created from block_scope's values
TargetGenerator::GenerateTarget(&block_scope, function, args, target_type, err);
```

After execution, the block scope is **destroyed** - but the target data is saved.

---

### Step 3: Parse BUILD.gn - Line 4: `update_target("//:my_target")`

```gn
update_target("//:my_target") { deps += [ ":helper" ] }
```

This does **NOT** execute the block yet! It just **registers** it:

```
┌─────────────────────────────────────────────────────────┐
│  GLOBAL SCOPE                                           │
│  │                                                      │
│  │  STATIC MAP: Scope::GetTargetUpdaters()              │
│  │  ┌─────────────────────────────────────────────┐     │
│  │  │  "//:my_target" → {                         │     │
│  │  │    updates: [                               │     │
│  │  │      (block_node, update_scope)  ← Stored!  │     │
│  │  │    ],                                       │     │
│  │  │    used: false                              │     │
│  │  │  }                                          │     │
│  │  └─────────────────────────────────────────────┘     │
│  │                                                      │
└─────────────────────────────────────────────────────────┘
```

**What happens internally** (see `chromium_src/gn/functions_target.cc:33-55`):

```cpp
Value RunUpdateTarget(Scope* scope, ..., BlockNode* block, ...) {
  const std::string& target_label = args[0].string_value();  // "//:my_target"

  // Get the global static map
  auto& updaters = Scope::GetTargetUpdaters();

  // Create an update_scope that remembers the current scope as parent
  std::unique_ptr<Scope> update_scope(new Scope(scope));

  // Store the block + scope for later execution
  updaters[target_label].updates.push_back(
      std::make_pair(block, std::move(update_scope)));

  return Value();  // Block is NOT executed yet!
}
```

The block `{ deps += [ ":helper" ] }` is **saved but not run**.

---

### Step 4: Parse BUILD.gn - Line 5: `group("my_target")`

```gn
group("my_target") { deps = [] }
```

Now GN creates a scope for this target AND applies the update:

```
┌─────────────────────────────────────────────────────────┐
│  GLOBAL SCOPE                                           │
│  │                                                      │
│  │  ┌─────────────────────────────────────────────┐     │
│  │  │  BLOCK SCOPE for group("my_target")         │     │
│  │  │  ├── target_name = "my_target"              │     │
│  │  │  ├── deps = []           ← Initially empty  │     │
│  │  │  └── (parent: GLOBAL SCOPE)                 │     │
│  │  └─────────────────────────────────────────────┘     │
│  │                      │                               │
│  │                      ▼                               │
│  │            UPDATE IS APPLIED HERE                    │
│  │                      │                               │
│  │                      ▼                               │
│  │  ┌─────────────────────────────────────────────┐     │
│  │  │  BLOCK SCOPE (after update)                 │     │
│  │  │  ├── target_name = "my_target"              │     │
│  │  │  ├── deps = [":helper"]  ← Updated!         │     │
│  │  │  └── (parent: GLOBAL SCOPE)                 │     │
│  │  └─────────────────────────────────────────────┘     │
│  │                                                      │
└─────────────────────────────────────────────────────────┘
```

**What happens internally** (see `chromium_src/gn/functions_target.cc:57-103`):

```cpp
// Called at the END of ExecuteGenericTarget(), after block executes
bool UpdateTheTarget(Scope* scope, ...) {
  // 1. Build the full label: "//:my_target"
  Label current_label = MakeLabelForScope(scope, function, "my_target");
  std::string full_label = current_label.GetUserVisibleName(true);

  // 2. Look up in the static map
  auto& updaters = Scope::GetTargetUpdaters();
  auto it = updaters.find(full_label);  // Found! "//:my_target" exists

  // 3. For each registered update...
  for (auto& update : it->second.updates) {
    // Create a temporary scope with the stored parent
    Scope update_scope(update.second.get());

    // 4. Execute the block: { deps += [ ":helper" ] }
    //    This reads `deps` from block_scope (gets [])
    //    Then appends ":helper" → deps = [":helper"]
    update.first->Execute(&update_scope, err);

    // 5. Merge the results back into the target's scope
    Scope::MergeOptions options;
    options.prefer_existing = true;   // Keep target's existing values
    options.skip_private_vars = true; // Don't copy _private vars
    options.mark_dest_used = true;    // Mark as used

    scope->NonRecursiveMergeTo(scope, options, ...);
  }
}
```

---

## The Magic: How `deps += [":helper"]` Works

When the update block executes:

```
┌────────────────────────────────────────────────────────────────┐
│  UPDATE_SCOPE (temporary)                                      │
│  ├── parent: stored_update_scope                               │
│  │   └── parent: GLOBAL SCOPE (from when update was registered)│
│  │                                                             │
│  │  Executing: deps += [ ":helper" ]                           │
│  │                                                             │
│  │  Step 1: Read `deps`                                        │
│  │          → Not in update_scope                              │
│  │          → Not in stored_update_scope                       │
│  │          → Check block_scope? NO! Not linked                │
│  │          → Result: deps = [] (or error if undefined)        │
│  │                                                             │
│  │  Step 2: Append ":helper"                                   │
│  │          → deps = [] + [":helper"] = [":helper"]            │
│  │                                                             │
│  │  Step 3: Write `deps` to update_scope                       │
│  │          → update_scope.deps = [":helper"]                  │
│  │                                                             │
└────────────────────────────────────────────────────────────────┘
                              │
                              ▼ NonRecursiveMergeTo()
┌────────────────────────────────────────────────────────────────┐
│  BLOCK_SCOPE (target's scope)                                  │
│  ├── deps = []  (before merge)                                 │
│  │                                                             │
│  │  Merge with prefer_existing = true:                         │
│  │  → block_scope has deps = []                                │
│  │  → update_scope has deps = [":helper"]                      │
│  │  → Result: deps = [":helper"]  (update wins for +=)         │
│  │                                                             │
│  └── deps = [":helper"]  (after merge)                         │
└────────────────────────────────────────────────────────────────┘
```

---

## Summary Diagram: Complete Flow

```
TIME
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 1. BUILDCONFIG.gn executes                                      │
│    → Global scope initialized                                   │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 2. source_set("helper") executes                                │
│    → Creates block_scope (child of global)                      │
│    → Sets sources = []                                          │
│    → Block_scope destroyed, target saved                        │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 3. update_target("//:my_target") called                         │
│    → Block { deps += [":helper"] } NOT executed                 │
│    → Stored in static map with scope snapshot                   │
└─────────────────────────────────────────────────────────────────┘
  │
  ▼
┌─────────────────────────────────────────────────────────────────┐
│ 4. group("my_target") executes                                  │
│    → Creates block_scope                                        │
│    → Runs { deps = [] }                                         │
│    → At END: UpdateTheTarget() called                           │
│      → Finds "//:my_target" in map                              │
│      → Executes stored block { deps += [":helper"] }            │
│      → Merges result into block_scope                           │
│    → Final deps = [":helper"]                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## Key Takeaways

| Concept | What It Does |
|---------|--------------|
| **Scope** | Container for variables during execution |
| **Parent scope** | Allows reading variables from outer contexts |
| **Static map** | Stores updates globally, keyed by target label |
| **Deferred execution** | Update block runs only when target is defined |
| **NonRecursiveMergeTo** | Copies variables from update scope to target scope |

The key insight is that `update_target` **doesn't modify anything when called** - it just stores the block for later. The actual modification happens inside `ExecuteGenericTarget()` after the target's own block runs.

## Testing

Verify the behavior:

```bash
cd test_project
../out/gn gen out --root=.
../out/gn desc out //:my_target deps      # Shows :helper was added
../out/gn desc out //:templated deps      # Shows :helper was added
```
