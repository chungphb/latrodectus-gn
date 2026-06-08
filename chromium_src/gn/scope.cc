#include "gn/scope_per_file_provider.h"
#include "gn/standard_out.h"
#include "gn/target.h"

// Hook in NonRecursiveMergeTo() to support prefer_existing option.
// Skips merging if destination already has the value.
#define LATRODECTUS_GN_SCOPE_NON_RECURSIVE_MERGE_TO \
  if (options.prefer_existing) {               \
    if (options.mark_dest_used) {              \
      dest->MarkUsed(current_name);            \
    }                                          \
    continue;                                  \
  }

#include "../../gn/src/gn/scope.cc"

#undef LATRODECTUS_GN_SCOPE_NON_RECURSIVE_MERGE_TO

// Static member definitions
Scope::UpdateParseItem::UpdateParseItem() {}
Scope::UpdateParseItem::~UpdateParseItem() = default;

Scope::UpdateParseMap Scope::target_update_list;
Scope::UpdateParseMap Scope::template_update_list;
Scope::UpdateParseMap Scope::file_update_list;
Scope::DisabledTargetMap Scope::disabled_targets;
Scope::DisabledTemplateInstanceMap Scope::disabled_template_instances;
Scope::DisabledFileMap Scope::disabled_files;
Scope::DeclaredUpdatersMap Scope::declared_updaters;

// Verify all update_target/update_template_instance/disable_target calls were
// used
namespace {
bool VerifyAllUpdatesInListUsed(Scope::UpdateParseMap& map,
                                const std::string& name,
                                Err* err) {
  for (const auto& it : map) {
    if (!it.second.used && !it.second.updates.empty()) {
      std::string help = "You set " + name + " updates of the label \"" +
                         it.first +
                         "\" here and it was unused when the project was "
                         "finished.\n";
      *err = it.second.updates[0].first->MakeErrorDescribing(
          "Unused " + name + " update.", help);
      return false;
    }
  }
  return true;
}

bool VerifyAllDisabledTargetsUsed(Scope::DisabledTargetMap& map, Err* err) {
  for (const auto& it : map) {
    if (!it.second.used && it.second.origin) {
      std::string help = "You set disable_target for the label \"" + it.first +
                         "\" here but it was never matched.\n";
      *err =
          it.second.origin->MakeErrorDescribing("Unused disable_target.", help);
      return false;
    }
  }
  return true;
}

bool VerifyAllDisabledTemplateInstancesUsed(
    Scope::DisabledTemplateInstanceMap& map,
    Err* err) {
  for (const auto& it : map) {
    if (!it.second.used && it.second.origin) {
      std::string help = "You set disable_template_instance for the label \"" +
                         it.first + "\" here but it was never matched.\n";
      *err = it.second.origin->MakeErrorDescribing(
          "Unused disable_template_instance.", help);
      return false;
    }
  }
  return true;
}

bool VerifyAllDisabledFilesUsed(Scope::DisabledFileMap& map, Err* err) {
  for (const auto& it : map) {
    if (!it.second.used && it.second.origin) {
      std::string help = "You set disable_file for the path \"" + it.first +
                         "\" here but it was never matched.\n";
      *err =
          it.second.origin->MakeErrorDescribing("Unused disable_file.", help);
      return false;
    }
  }
  return true;
}

bool VerifyAllFileUpdatesUsed(Scope::UpdateParseMap& map, Err* err) {
  for (const auto& it : map) {
    if (!it.second.used && !it.second.updates.empty()) {
      std::string help = "You set update_file for the path \"" + it.first +
                         "\" here but it was never matched.\n";
      *err = it.second.updates[0].first->MakeErrorDescribing(
          "Unused update_file.", help);
      return false;
    }
  }
  return true;
}
}  // namespace

bool Scope::VerifyAllUpdatesUsed(Err* err) {
  return (
      VerifyAllUpdatesInListUsed(target_update_list, "update_target", err) &&
      VerifyAllUpdatesInListUsed(template_update_list,
                                 "update_template_instance", err) &&
      VerifyAllFileUpdatesUsed(file_update_list, err) &&
      VerifyAllDisabledTargetsUsed(disabled_targets, err) &&
      VerifyAllDisabledTemplateInstancesUsed(disabled_template_instances,
                                             err) &&
      VerifyAllDisabledFilesUsed(disabled_files, err));
}

bool Scope::IsFileDisabled(const std::string& file_path) {
  return disabled_files.find(file_path) != disabled_files.end();
}

void Scope::MarkFileDisabledUsed(const std::string& file_path) {
  auto it = disabled_files.find(file_path);
  if (it != disabled_files.end()) {
    it->second.used = true;
  }
}

bool Scope::CheckDepsOnDisabledTargets(
    const std::vector<const Target*>& targets,
    Err* err) {
  if (disabled_targets.empty()) {
    return true;
  }

  for (const Target* target : targets) {
    // Check all dependency types
    const LabelTargetVector* dep_lists[] = {
        &target->private_deps(),
        &target->public_deps(),
        &target->data_deps(),
    };

    for (const LabelTargetVector* deps : dep_lists) {
      for (const auto& dep : *deps) {
        std::string dep_label = dep.label.GetUserVisibleName(false);

        // Check exact match
        bool is_disabled =
            disabled_targets.find(dep_label) != disabled_targets.end();

        // Check wildcard match (//foo:* matches //foo:bar)
        if (!is_disabled) {
          size_t colon_pos = dep_label.rfind(':');
          if (colon_pos != std::string::npos) {
            std::string wildcard = dep_label.substr(0, colon_pos + 1) + "*";
            is_disabled =
                disabled_targets.find(wildcard) != disabled_targets.end();
          }
        }

        if (is_disabled) {
          std::string msg = "Target " +
                            target->label().GetUserVisibleName(false) +
                            " depends on disabled target " + dep_label + ".\n";
          if (dep.origin) {
            *err = Err(dep.origin, "Dependency on disabled target.", msg);
          } else {
            *err = Err(target->defined_from(), "Dependency on disabled target.",
                       msg);
          }
          return false;
        }
      }
    }
  }
  return true;
}

bool Scope::CheckDepsOnDisabledTemplateInstances(
    const std::vector<const Target*>& targets,
    Err* err) {
  if (disabled_template_instances.empty()) {
    return true;
  }

  for (const Target* target : targets) {
    // Check all dependency types
    const LabelTargetVector* dep_lists[] = {
        &target->private_deps(),
        &target->public_deps(),
        &target->data_deps(),
    };

    for (const LabelTargetVector* deps : dep_lists) {
      for (const auto& dep : *deps) {
        std::string dep_label = dep.label.GetUserVisibleName(false);

        // Check exact match
        bool is_disabled = disabled_template_instances.find(dep_label) !=
                           disabled_template_instances.end();

        // Check wildcard match (//foo:* matches //foo:bar)
        if (!is_disabled) {
          size_t colon_pos = dep_label.rfind(':');
          if (colon_pos != std::string::npos) {
            std::string wildcard = dep_label.substr(0, colon_pos + 1) + "*";
            is_disabled = disabled_template_instances.find(wildcard) !=
                          disabled_template_instances.end();
          }
        }

        if (is_disabled) {
          std::string msg =
              "Target " + target->label().GetUserVisibleName(false) +
              " depends on disabled template instance " + dep_label + ".\n";
          if (dep.origin) {
            *err = Err(dep.origin, "Dependency on disabled template instance.",
                       msg);
          } else {
            *err = Err(target->defined_from(),
                       "Dependency on disabled template instance.", msg);
          }
          return false;
        }
      }
    }
  }
  return true;
}

bool Scope::ApplyFileUpdates(const std::string& file_path,
                             Scope* scope,
                             Err* err) {
  auto& updaters = file_update_list;
  auto it = updaters.find(file_path);

  // No updates registered for this file.
  if (it == updaters.end()) {
    return true;
  }

  // Already applied (defensive check - import caching should prevent this).
  if (it->second.used) {
    return true;
  }

  it->second.used = true;

  // Apply each registered update in order. Each update contains the block
  // to execute (update.first) and the SAVED SCOPE captured at registration
  // time (update.second).
  for (auto& update : it->second.updates) {
    // Create EXTRA SCOPE as child of SAVED SCOPE so the update block can
    // access variables from where update_file() was called.
    Scope extra_scope(update.second.get());

    // Merge FILE SCOPE variables into EXTRA SCOPE so they're accessible
    // and take precedence over saved scope variables.
    Scope::MergeOptions prefer_options;
    prefer_options.prefer_existing = true;
    scope->NonRecursiveMergeTo(&extra_scope, prefer_options, nullptr,
                               "update_file file vars", err);
    if (err->has_error()) {
      return false;
    }

    // Execute the update block in BLOCK SCOPE.
    Scope block_scope(&extra_scope);
    ScopePerFileProvider per_file_provider(&block_scope, true);
    update.first->Execute(&block_scope, err);
    if (err->has_error()) {
      return false;
    }

    // Mark all variables in both scopes as used to prevent "assignment had
    // no effect" warnings. The variables will be merged to the file scope.
    extra_scope.MarkAllUsed();
    block_scope.MarkAllUsed();

    // Merge BLOCK SCOPE back into FILE SCOPE with clobber_existing,
    // so the update values override the originals.
    Scope::MergeOptions clobber_options;
    clobber_options.clobber_existing = true;
    clobber_options.mark_dest_used = true;
    block_scope.NonRecursiveMergeTo(scope, clobber_options, nullptr,
                                    "update_file merge", err);
    if (err->has_error()) {
      return false;
    }
  }

  return true;
}
