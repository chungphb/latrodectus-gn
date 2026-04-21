// Hook in DoImport() to check for declared updaters and import them first.
// Placed at the start of DoImport() before any import logic.
#define LATRODECTUS_GN_IMPORT_MANAGER_DO_IMPORT                                 \
  {                                                                        \
    auto& declared = Scope::GetDeclaredUpdaters();                         \
    auto it = declared.find(file.value());                                 \
    if (it != declared.end()) {                                            \
      std::string updater_path = it->second;                               \
      declared.erase(it);                                                  \
      if (!DoImport(SourceFile(updater_path), node_for_err, scope, err)) { \
        return false;                                                      \
      }                                                                    \
    }                                                                      \
  }

// Hook in UncachedImport() to apply .gni file updates after execution.
// Placed right after node->Execute() to modify variables before they're cached.
#define LATRODECTUS_GN_IMPORT_MANAGER_UNCACHED_IMPORT                     \
  if (!err->has_error() &&                                           \
      !Scope::ApplyFileUpdates(file.value(), scope.get(), err)) {    \
    err->AppendSubErr(Err(node_for_err, "whence it was imported.")); \
    return nullptr;                                                  \
  }

#include "../../gn/src/gn/import_manager.cc"

#undef LATRODECTUS_GN_IMPORT_MANAGER_DO_IMPORT
#undef LATRODECTUS_GN_IMPORT_MANAGER_UNCACHED_IMPORT
