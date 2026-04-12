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

  const std::string& target_label = args[0].string_value();
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
    // Merge SAVED SCOPE into EXTRA SCOPE with prefer_existing,
    // so target's current values take precedence over saved values.
    Scope::MergeOptions prefer_options;
    prefer_options.prefer_existing = true;
    Scope extra_scope(scope);
    update.second->NonRecursiveMergeTo(&extra_scope, prefer_options, function,
                                       "update_target import", err);
    if (err->has_error()) {
      return false;
    }

    // Execute the update block in BLOCK SCOPE.
    Scope block_scope(&extra_scope);
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

  const std::string& template_name = args[0].string_value();
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
    // Merge SAVED SCOPE into EXTRA SCOPE with prefer_existing,
    // so target's current values take precedence over saved values.
    Scope::MergeOptions prefer_options;
    prefer_options.prefer_existing = true;
    Scope extra_scope(scope);
    update.second->NonRecursiveMergeTo(&extra_scope, prefer_options, function,
                                       "update_template import", err);
    if (err->has_error()) {
      return false;
    }

    // Execute the update block in BLOCK SCOPE.
    Scope block_scope(&extra_scope);
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

  const std::string& target_label = args[0].string_value();
  auto& disabled = Scope::GetDisabledTargets();
  disabled[target_label].origin = function;

  return Value();
}

// Checks if a target is disabled by looking up its label.
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
  auto it = disabled.find(lookup_label);
  if (it != disabled.end()) {
    it->second.used = true;
    return true;
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
}

}  // namespace functions
