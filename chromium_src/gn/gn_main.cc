// Override version output to show "(Latrodectus)" suffix
#define LATRODECTUS_GN_GN_MAIN_VERSION_OUTPUT                           \
  OutputString(std::string(LAST_COMMIT_POSITION) + " (Latrodectus)\n"); \
  if (false)

#include "../../gn/src/gn/gn_main.cc"

#undef LATRODECTUS_GN_GN_MAIN_VERSION_OUTPUT
