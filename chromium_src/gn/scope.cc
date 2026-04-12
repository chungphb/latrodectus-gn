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
Scope::DisabledTargetMap Scope::disabled_targets;
Scope::DisabledFileMap Scope::disabled_files;

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
}  // namespace

bool Scope::VerifyAllUpdatesUsed(Err* err) {
  return (
      VerifyAllUpdatesInListUsed(target_update_list, "update_target", err) &&
      VerifyAllUpdatesInListUsed(template_update_list,
                                 "update_template_instance", err) &&
      VerifyAllDisabledTargetsUsed(disabled_targets, err) &&
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
