// Hook in ExecuteGenericTarget() after block execution.
// Applies any pending update_target() modifications to the target.
#define LATRODECTUS_GN_FUNCTIONS_TARGET_EXECUTE_GENERIC_TARGET           \
  if (!UpdateTheTarget(&block_scope, function, args, block, err)) { \
    return Value();                                                 \
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

  // Build the full target label (e.g., "//:my_target") to look up updates.
  const std::string& target_name = args[0].string_value();
  Label current_label = MakeLabelForScope(scope, function, target_name);
  std::string full_label = current_label.GetUserVisibleName(true);

  auto& updaters = Scope::GetTargetUpdaters();
  auto it = updaters.find(full_label);

  // No updates registered for this target.
  if (it == updaters.end()) {
    return true;
  }

  // Prevent applying updates multiple times to the same target.
  // This can happen when the same BUILD.gn is processed for multiple
  // toolchains - each toolchain invokes the target definition again.
  if (it->second.targets_done.count(target_name)) {
    return true;
  }

  it->second.used = true;
  it->second.targets_done.insert(target_name);

  // Apply each registered update in order.
  for (auto& update : it->second.updates) {
    // Keep target's existing values, don't copy _private variables,
    // and mark merged vars as used.
    Scope::MergeOptions options;
    options.prefer_existing = true;
    options.skip_private_vars = true;
    options.mark_dest_used = true;

    // Execute the update block in a temporary scope.
    Scope update_scope(update.second.get());
    update.first->Execute(&update_scope, err);
    if (err->has_error()) {
      return false;
    }

    // Merge the update results into the target's scope.
    scope->NonRecursiveMergeTo(scope, options, update.first, "update_target",
                               err);
    if (err->has_error()) {
      return false;
    }
  }

  return true;
}

// update_template_instance ----------------------------------------------------
const char kUpdateTemplate[] = "update_template_instance";
const char kUpdateTemplate_HelpShort[] =
    "update_template_instance: Modify targets created by a template.";
const char kUpdateTemplate_Help[] =
    R"(update_template_instance: Modify targets created by a template.

  update_template_instance(template_name) {
    # modifications
  }

  Allows modifying properties of targets created by a specific template.

Example:
  update_template_instance("component") {
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

// Called when a target is created inside a template to apply template updates.
// Uses the template invocation stack to determine which template created
// the current target.
bool UpdateTheTemplate(Scope* scope,
                       const FunctionCallNode* function,
                       const std::vector<Value>& args,
                       BlockNode* block,
                       Err* err,
                       Scope* function_scope) {
  std::vector<Scope::TemplateInvocationEntry> entries =
      scope->GetTemplateInvocationEntries();

  // Not inside a template.
  if (entries.empty()) {
    return true;
  }

  // Use the most recent (innermost) template invocation.
  const std::string& template_name = entries.back().template_name;
  auto& updaters = Scope::GetTemplateInstanceUpdaters();
  auto it = updaters.find(template_name);

  // No updates registered for this template.
  if (it == updaters.end()) {
    return true;
  }

  it->second.used = true;

  // Apply each registered update in order.
  for (auto& update : it->second.updates) {
    // Keep target's existing values, don't copy _private variables,
    // and mark merged vars as used.
    Scope::MergeOptions options;
    options.prefer_existing = true;
    options.skip_private_vars = true;
    options.mark_dest_used = true;

    // Execute the update block in a temporary scope.
    Scope update_scope(update.second.get());
    update.first->Execute(&update_scope, err);
    if (err->has_error()) {
      return false;
    }

    // Merge into the function scope (the scope where the target is defined).
    function_scope->NonRecursiveMergeTo(function_scope, options, update.first,
                                        "update_template_instance", err);
    if (err->has_error()) {
      return false;
    }
  }

  return true;
}

}  // namespace functions
