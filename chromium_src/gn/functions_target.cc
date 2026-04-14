#include "gn/scope_per_file_provider.h"

// Hook in ExecuteGenericTarget() after block execution.
// First checks if target is disabled, then applies any pending updates.
#define LATRODECTUS_GN_FUNCTIONS_TARGET_EXECUTE_GENERIC_TARGET                  \
  if (IsTargetDisabled(&block_scope, function, args)) {                    \
    ClearTargetScope(&block_scope);                                        \
  } else if (!UpdateTheTarget(&block_scope, function, args, block, err)) { \
    return Value();                                                        \
  }

#include "../../gn/src/gn/functions_target.cc"

#undef LATRODECTUS_GN_FUNCTIONS_TARGET_EXECUTE_GENERIC_TARGET

namespace functions {

// update_target ---------------------------------------------------------------
const char kUpdateTarget[] = "update_target";
const char kUpdateTarget_HelpShort[] =
    "update_target: Modify an existing target.";
const char kUpdateTarget_Help[] =
    R"(update_target: Modify an existing target.

  update_target(target_label) {
    # modifications
  }

  Allows modifying properties of a target after it has been defined.
  The target_label should match the label used when the target was defined.

Example:
  update_target("//foo:bar") {
    deps += [ "//extra:dep" ]
  }
)";

// Registers an update block to be applied later when the target is defined.
// The block is NOT executed here - it's stored along with a scope snapshot
// for deferred execution in UpdateTheTarget().
//
// Multiple update_target() calls for the same label are allowed and will be
// applied in order when the target is defined.
// Normalizes a label string to fully-qualified form.
// - "//foo/bar" -> "//foo/bar:bar" (add implicit target name)
// - "//foo/bar:baz" -> "//foo/bar:baz" (already has target name)
// - "//:foo" -> "//:foo" (root label already has target name)
// - "bar" -> "<source_dir>:bar" (relative target name)
std::string NormalizeLabelForScope(Scope* scope,
                                   const FunctionCallNode* function,
                                   const std::string& input) {
  // If label already has a colon after //, it's already fully qualified
  if (input.size() >= 2 && input[0] == '/' && input[1] == '/') {
    size_t colon_pos = input.find(':');
    if (colon_pos != std::string::npos) {
      // Already has :target_name, use as-is
      return input;
    }
    // No colon - add implicit target name from last path component
    // e.g., "//foo/bar" -> "//foo/bar:bar"
    size_t last_slash = input.rfind('/');
    if (last_slash != std::string::npos && last_slash >= 2) {
      std::string dir_name = input.substr(last_slash + 1);
      return input + ":" + dir_name;
    }
    // Root case: "//" -> "//:BUILD.gn" (shouldn't happen in practice)
    return input;
  }
  // Relative target name - use MakeLabelForScope
  Label label = MakeLabelForScope(scope, function, input);
  return label.GetUserVisibleName(false);
}

Value RunUpdateTarget(Scope* scope,
                      const FunctionCallNode* function,
                      const std::vector<Value>& args,
                      BlockNode* block,
                      Err* err) {
  if (args.size() != 1) {
    *err = Err(function, "update_target requires exactly one argument.");
    return Value();
  }

  if (!args[0].VerifyTypeIs(Value::STRING, err)) {
    return Value();
  }

  // Normalize the label to fully-qualified form (//foo/bar -> //foo/bar:bar)
  // so it matches the lookup in UpdateTheTarget.
  const std::string& target_label_input = args[0].string_value();
  std::string target_label =
      NormalizeLabelForScope(scope, function, target_label_input);

  auto& updaters = Scope::GetTargetUpdaters();

  // Create a scope snapshot that captures the current scope as parent.
  // This allows the update block to access variables from the context
  // where update_target() was called.
  std::unique_ptr<Scope> update_scope(new Scope(scope));

  // Store the block and scope for later execution. Using push_back allows
  // multiple updates for the same target label.
  updaters[target_label].updates.push_back(
      std::make_pair(block, std::move(update_scope)));

  return Value();
}

// Called at the end of ExecuteGenericTarget() to apply any pending updates.
// This is where the deferred update blocks registered by RunUpdateTarget()
// are actually executed and merged into the target's scope.
bool UpdateTheTarget(Scope* scope,
                     const FunctionCallNode* function,
                     const std::vector<Value>& args,
                     BlockNode* block,
                     Err* err) {
  if (args.empty()) {
    return true;
  }

  // Build target labels for lookup and tracking.
  // Lookup uses label WITHOUT toolchain (matches all toolchain variants).
  // Tracking uses label WITH toolchain (each variant updated once).
  const std::string& target_name = args[0].string_value();
  Label current_label = MakeLabelForScope(scope, function, target_name);
  std::string lookup_label = current_label.GetUserVisibleName(false);
  std::string tracking_label = current_label.GetUserVisibleName(true);

  auto& updaters = Scope::GetTargetUpdaters();
  auto it = updaters.find(lookup_label);

  // No updates registered for this target.
  if (it == updaters.end()) {
    return true;
  }

  // Prevent applying updates multiple times to the same target+toolchain.
  // Each toolchain variant is updated independently.
  if (it->second.targets_done.count(tracking_label)) {
    return true;
  }

  it->second.used = true;
  it->second.targets_done.insert(tracking_label);

  // Apply each registered update in order. Each update contains the block
  // to execute (update.first) and the SAVED SCOPE captured at registration
  // time (update.second).
  for (auto& update : it->second.updates) {
    // Create EXTRA SCOPE as child of SAVED SCOPE so the update block can
    // access variables from where update_target() was called (like config
    // flags imported at that time).
    Scope extra_scope(update.second.get());

    // Merge TARGET SCOPE variables into EXTRA SCOPE so they're accessible
    // and take precedence over saved scope variables.
    Scope::MergeOptions prefer_options;
    prefer_options.prefer_existing = true;
    scope->NonRecursiveMergeTo(&extra_scope, prefer_options, function,
                               "update_target target vars", err);
    if (err->has_error()) {
      return false;
    }

    // Execute the update block in BLOCK SCOPE.
    // Add ScopePerFileProvider to provide built-in variables like root_gen_dir
    // that were available during import but whose provider was destroyed.
    Scope block_scope(&extra_scope);
    ScopePerFileProvider per_file_provider(&block_scope, true);
    update.first->Execute(&block_scope, err);
    if (err->has_error()) {
      return false;
    }

    // Merge BLOCK SCOPE back into TARGET SCOPE with clobber_existing,
    // so the update values override the originals.
    Scope::MergeOptions clobber_options;
    clobber_options.clobber_existing = true;
    block_scope.NonRecursiveMergeTo(scope, clobber_options, function,
                                    "update_target merge", err);
    if (err->has_error()) {
      return false;
    }
  }

  return true;
}

// update_template_instance ----------------------------------------------------
const char kUpdateTemplate[] = "update_template_instance";
const char kUpdateTemplate_HelpShort[] =
    "update_template_instance: Modify a template instantiation by label.";
const char kUpdateTemplate_Help[] =
    R"(update_template_instance: Modify a template instantiation by label.

  update_template_instance(target_label) {
    # modifications
  }

  Allows modifying properties of a target created by a template instantiation.
  The target_label should match the label of the template instantiation.

Example:
  update_template_instance("//foo:bar") {
    deps += [ "//extra:dep" ]
  }
)";

// Registers an update block for template instances.
// Similar to RunUpdateTarget(), the block is stored for deferred execution
// when targets are created by the specified template.
Value RunUpdateTemplate(Scope* scope,
                        const FunctionCallNode* function,
                        const std::vector<Value>& args,
                        BlockNode* block,
                        Err* err) {
  if (args.size() != 1) {
    *err = Err(function,
               "update_template_instance requires exactly one argument.");
    return Value();
  }

  if (!args[0].VerifyTypeIs(Value::STRING, err)) {
    return Value();
  }

  // Normalize the label to fully-qualified form (//foo/bar -> //foo/bar:bar)
  // so it matches the lookup in UpdateTheTemplate.
  const std::string& template_name_input = args[0].string_value();
  std::string template_name =
      NormalizeLabelForScope(scope, function, template_name_input);

  auto& updaters = Scope::GetTemplateInstanceUpdaters();

  std::unique_ptr<Scope> update_scope(new Scope(scope));
  updaters[template_name].updates.push_back(
      std::make_pair(block, std::move(update_scope)));

  return Value();
}

// Called during template instantiation to apply template updates.
// Uses label-based lookup similar to UpdateTheTarget.
bool UpdateTheTemplate(Scope* scope,
                       const FunctionCallNode* function,
                       const std::vector<Value>& args,
                       BlockNode* block,
                       Err* err,
                       Scope* function_scope) {
  if (args.empty()) {
    return true;
  }

  // Build target labels for lookup and tracking.
  // Use function_scope (outer scope) for source dir resolution.
  const std::string& target_name = args[0].string_value();
  Label current_label =
      MakeLabelForScope(function_scope, function, target_name);
  std::string lookup_label = current_label.GetUserVisibleName(false);
  std::string tracking_label = current_label.GetUserVisibleName(true);

  auto& updaters = Scope::GetTemplateInstanceUpdaters();
  auto it = updaters.find(lookup_label);

  // No updates registered for this target.
  if (it == updaters.end()) {
    return true;
  }

  // Prevent applying updates multiple times to the same target+toolchain.
  if (it->second.targets_done.count(tracking_label)) {
    return true;
  }

  it->second.used = true;
  it->second.targets_done.insert(tracking_label);

  // Apply each registered update in order. Each update contains the block
  // to execute (update.first) and the SAVED SCOPE captured at registration
  // time (update.second).
  for (auto& update : it->second.updates) {
    // Create EXTRA SCOPE as child of SAVED SCOPE so the update block can
    // access variables from where update_template_instance() was called.
    Scope extra_scope(update.second.get());

    // Merge TARGET SCOPE variables into EXTRA SCOPE so they're accessible
    // and take precedence over saved scope variables.
    Scope::MergeOptions prefer_options;
    prefer_options.prefer_existing = true;
    scope->NonRecursiveMergeTo(&extra_scope, prefer_options, function,
                               "update_template target vars", err);
    if (err->has_error()) {
      return false;
    }

    // Execute the update block in BLOCK SCOPE.
    // Add ScopePerFileProvider to provide built-in variables like root_gen_dir
    // that were available during import but whose provider was destroyed.
    Scope block_scope(&extra_scope);
    ScopePerFileProvider per_file_provider(&block_scope, true);
    update.first->Execute(&block_scope, err);
    if (err->has_error()) {
      return false;
    }

    // Merge BLOCK SCOPE back into TARGET SCOPE with clobber_existing,
    // so the update values override the originals.
    Scope::MergeOptions clobber_options;
    clobber_options.clobber_existing = true;
    block_scope.NonRecursiveMergeTo(scope, clobber_options, function,
                                    "update_template merge", err);
    if (err->has_error()) {
      return false;
    }
  }

  return true;
}

// disable_target
// ---------------------------------------------------------------
const char kDisableTarget[] = "disable_target";
const char kDisableTarget_HelpShort[] =
    "disable_target: Disable a target, making it a no-op.";
const char kDisableTarget_Help[] =
    R"(disable_target: Disable a target, making it a no-op.

  disable_target(target_label)

  Marks a target to be disabled. When the target is defined, it will be
  converted to an empty target with no sources or deps. This is useful for
  excluding targets without patching the original BUILD.gn files.

  The target_label should match the label used when the target is defined.

Example:
  disable_target("//foo:bar")
)";

// Registers a target to be disabled. The target will still be defined
// but will have no sources, deps, or other properties.
Value RunDisableTarget(Scope* scope,
                       const FunctionCallNode* function,
                       const std::vector<Value>& args,
                       Err* err) {
  if (args.size() != 1) {
    *err = Err(function, "disable_target requires exactly one argument.");
    return Value();
  }

  if (!args[0].VerifyTypeIs(Value::STRING, err)) {
    return Value();
  }

  const std::string& target_label_input = args[0].string_value();
  auto& disabled = Scope::GetDisabledTargets();

  // Check for wildcard pattern (//foo:*)
  if (target_label_input.size() >= 2 &&
      target_label_input.substr(target_label_input.size() - 2) == ":*") {
    // Store wildcard patterns as-is
    disabled[target_label_input].origin = function;
  } else {
    // Normalize the label to fully-qualified form (//foo/bar -> //foo/bar:bar)
    // so it matches the lookup in IsTargetDisabled.
    std::string target_label =
        NormalizeLabelForScope(scope, function, target_label_input);
    disabled[target_label].origin = function;
  }

  return Value();
}

// Checks if a target is disabled by looking up its label.
// Supports both exact match (//foo:bar) and wildcard (//foo:*).
// Marks the disabled target as used when matched.
bool IsTargetDisabled(Scope* scope,
                      const FunctionCallNode* function,
                      const std::vector<Value>& args) {
  if (args.empty()) {
    return false;
  }

  const std::string& target_name = args[0].string_value();
  Label current_label = MakeLabelForScope(scope, function, target_name);
  std::string lookup_label = current_label.GetUserVisibleName(false);

  auto& disabled = Scope::GetDisabledTargets();

  // Check exact match
  auto it = disabled.find(lookup_label);
  if (it != disabled.end()) {
    it->second.used = true;
    return true;
  }

  // Check wildcard match (//foo:* matches //foo:bar)
  size_t colon_pos = lookup_label.rfind(':');
  if (colon_pos != std::string::npos) {
    std::string wildcard_label = lookup_label.substr(0, colon_pos + 1) + "*";
    auto wit = disabled.find(wildcard_label);
    if (wit != disabled.end()) {
      wit->second.used = true;
      return true;
    }
  }

  return false;
}

// Clears common target variables from the scope, making it an empty target.
void ClearTargetScope(Scope* scope) {
  scope->SetValue("sources", Value(nullptr, Value::LIST), nullptr);
  scope->SetValue("deps", Value(nullptr, Value::LIST), nullptr);
  scope->SetValue("public_deps", Value(nullptr, Value::LIST), nullptr);
  scope->SetValue("data_deps", Value(nullptr, Value::LIST), nullptr);
  scope->SetValue("inputs", Value(nullptr, Value::LIST), nullptr);
  scope->SetValue("data", Value(nullptr, Value::LIST), nullptr);
  scope->SetValue("defines", Value(nullptr, Value::LIST), nullptr);
}

// disable_file
// ---------------------------------------------------------------
const char kDisableFile[] = "disable_file";
const char kDisableFile_HelpShort[] =
    "disable_file: Prevent a BUILD.gn file from being loaded.";
const char kDisableFile_Help[] =
    R"(disable_file: Prevent a BUILD.gn file from being loaded.

  disable_file(file_path)

  Marks a BUILD.gn file to be skipped during loading. When GN attempts to
  load the file, it will be treated as an empty file. This is useful for
  excluding entire directories without patching the original BUILD.gn files.

  The file_path should be the full path starting with // (e.g.,
  "//foo/bar/BUILD.gn").

  Unlike disable_target(), this prevents the file from being parsed at all,
  which avoids issues with declare_args() conflicts and top-level asserts.

Example:
  disable_file("//third_party/unwanted/BUILD.gn")
)";

// Registers a file to be disabled. The file will not be loaded or parsed.
Value RunDisableFile(Scope* scope,
                     const FunctionCallNode* function,
                     const std::vector<Value>& args,
                     Err* err) {
  if (args.size() != 1) {
    *err = Err(function, "disable_file requires exactly one argument.");
    return Value();
  }

  if (!args[0].VerifyTypeIs(Value::STRING, err)) {
    return Value();
  }

  const std::string& file_path = args[0].string_value();

  // Validate the path starts with //
  if (file_path.size() < 2 || file_path[0] != '/' || file_path[1] != '/') {
    *err = Err(args[0].origin(),
               "disable_file requires a full path starting with //.",
               "Got: \"" + file_path + "\"");
    return Value();
  }

  auto& disabled = Scope::GetDisabledFiles();
  disabled[file_path].origin = function;

  return Value();
}

}  // namespace functions
