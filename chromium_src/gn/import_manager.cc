// Hook in UncachedImport() to apply .gni file updates after execution.
// Placed right after node->Execute() to modify variables before they're cached.
#define LATRODECTUS_GN_IMPORT_MANAGER_UNCACHED_IMPORT                     \
  if (!err->has_error() &&                                           \
      !Scope::ApplyFileUpdates(file.value(), scope.get(), err)) {    \
    err->AppendSubErr(Err(node_for_err, "whence it was imported.")); \
    return nullptr;                                                  \
  }

#include "../../gn/src/gn/import_manager.cc"

#undef LATRODECTUS_GN_IMPORT_MANAGER_UNCACHED_IMPORT
