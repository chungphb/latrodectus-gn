// Hook in LoaderImpl::BackgroundLoadFile() to skip disabled files.
// Placed right after the "if (!root)" check to skip execution if the file
// is in the disabled files list.
#define LATRODECTUS_GN_LOADER_BACKGROUND_LOAD_FILE                        \
  if (Scope::IsFileDisabled(file_name.value())) {                    \
    Scope::MarkFileDisabledUsed(file_name.value());                  \
    if (g_scheduler->verbose_logging()) {                            \
      g_scheduler->Log("Skipping disabled file", file_name.value()); \
    }                                                                \
    task_runner_->PostTask([this]() { DidLoadFile(); });             \
    return;                                                          \
  }

#include "../../gn/src/gn/loader.cc"

#undef LATRODECTUS_GN_LOADER_BACKGROUND_LOAD_FILE
