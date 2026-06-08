// Hook in Setup::RunPostMessageLoop() to verify update_target usage.
// Closes original if block and opens new one with combined condition.
#define LATRODECTUS_GN_SETUP_RUN_POST_MESSAGE_LOOP                       \
  }                                                                 \
  if (!build_settings_.build_args().VerifyAllOverridesUsed(&err) || \
      !Scope::VerifyAllUpdatesUsed(&err)) {
#include "../../gn/src/gn/setup.cc"

#undef LATRODECTUS_GN_SETUP_RUN_POST_MESSAGE_LOOP
