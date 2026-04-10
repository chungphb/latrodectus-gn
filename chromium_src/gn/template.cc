// Hook in Template::Invoke() after the invocation block executes.
// Applies any pending update_template_instance() modifications.
#define LATRODECTUS_GN_TEMPLATE_INVOKE                                             \
  if (!functions::UpdateTheTemplate(invocation_scope.get(), invocation, args, \
                                    block, err, scope)) {                     \
    return Value();                                                           \
  }

#include "../../gn/src/gn/template.cc"

#undef LATRODECTUS_GN_TEMPLATE_INVOKE
