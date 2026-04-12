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
}  // namespace

bool Scope::VerifyAllUpdatesUsed(Err* err) {
  return (
      VerifyAllUpdatesInListUsed(target_update_list, "update_target", err) &&
      VerifyAllUpdatesInListUsed(template_update_list,
                                 "update_template_instance", err) &&
      VerifyAllDisabledTargetsUsed(disabled_targets, err));
}
