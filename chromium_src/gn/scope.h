#ifndef LATRODECTUS_CHROMIUM_SRC_GN_SCOPE_H_
#define LATRODECTUS_CHROMIUM_SRC_GN_SCOPE_H_

class Target;

// Hook to inject prefer_existing into MergeOptions
#define clobber_existing \
  clobber_existing;      \
  bool prefer_existing = false

// Hook to inject update_target types, getters, and static members
#define template_invocation_entry_                                         \
  template_invocation_entry_;                                              \
                                                                           \
 public:                                                                   \
  using UpdateParseListElement =                                           \
      std::pair<const ParseNode*, std::unique_ptr<Scope>>;                 \
  using UpdateParseList = std::vector<UpdateParseListElement>;             \
  using UpdatedTargetSet = std::set<std::string>;                          \
  struct UpdateParseItem {                                                 \
    bool used = false;                                                     \
    UpdateParseList updates;                                               \
    UpdatedTargetSet targets_done;                                         \
    UpdateParseItem();                                                     \
    ~UpdateParseItem();                                                    \
  };                                                                       \
  using UpdateParseMap = std::map<std::string, UpdateParseItem>;           \
  static UpdateParseMap& GetTargetUpdaters() {                             \
    return target_update_list;                                             \
  }                                                                        \
  static UpdateParseMap& GetTemplateInstanceUpdaters() {                   \
    return template_update_list;                                           \
  }                                                                        \
  struct DisabledTargetItem {                                              \
    bool used = false;                                                     \
    const ParseNode* origin = nullptr;                                     \
  };                                                                       \
  using DisabledTargetMap = std::map<std::string, DisabledTargetItem>;     \
  static DisabledTargetMap& GetDisabledTargets() {                         \
    return disabled_targets;                                               \
  }                                                                        \
  using DisabledTemplateInstanceMap =                                      \
      std::map<std::string, DisabledTargetItem>;                           \
  static DisabledTemplateInstanceMap& GetDisabledTemplateInstances() {     \
    return disabled_template_instances;                                    \
  }                                                                        \
  struct DisabledFileItem {                                                \
    bool used = false;                                                     \
    const ParseNode* origin = nullptr;                                     \
  };                                                                       \
  using DisabledFileMap = std::map<std::string, DisabledFileItem>;         \
  static DisabledFileMap& GetDisabledFiles() {                             \
    return disabled_files;                                                 \
  }                                                                        \
  static UpdateParseMap& GetFileUpdaters() {                               \
    return file_update_list;                                               \
  }                                                                        \
  using DeclaredUpdatersMap = std::map<std::string, std::string>;          \
  static DeclaredUpdatersMap& GetDeclaredUpdaters() {                      \
    return declared_updaters;                                              \
  }                                                                        \
  static bool VerifyAllUpdatesUsed(Err* err);                              \
  static bool CheckDepsOnDisabledTargets(                                  \
      const std::vector<const Target*>& targets, Err* err);                \
  static bool CheckDepsOnDisabledTemplateInstances(                        \
      const std::vector<const Target*>& targets, Err* err);                \
  static bool IsFileDisabled(const std::string& file_path);                \
  static void MarkFileDisabledUsed(const std::string& file_path);          \
  static bool ApplyFileUpdates(const std::string& file_path, Scope* scope, \
                               Err* err);                                  \
                                                                           \
 private:                                                                  \
  static UpdateParseMap target_update_list;                                \
  static UpdateParseMap template_update_list;                              \
  static UpdateParseMap file_update_list;                                  \
  static DisabledTargetMap disabled_targets;                               \
  static DisabledTemplateInstanceMap disabled_template_instances;          \
  static DisabledFileMap disabled_files;                                   \
  static DeclaredUpdatersMap declared_updaters

#include "../../gn/src/gn/scope.h"

#undef clobber_existing
#undef template_invocation_entry_

#endif  // LATRODECTUS_CHROMIUM_SRC_GN_SCOPE_H_
