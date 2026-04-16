#include "gn/target_generator.h"

// Hook in Template::Invoke() after the invocation block executes.
// First checks if the template instance is disabled, then applies any pending
// update_template_instance() modifications.
// When disabled, creates a placeholder group target so that dependencies on
// the disabled instance can be detected by
// CheckDepsOnDisabledTemplateInstances.
#define LATRODECTUS_GN_TEMPLATE_INVOKE                                              \
  if (functions::IsTemplateInstanceDisabled(scope, invocation, args)) {        \
    Scope placeholder_scope(scope);                                            \
    placeholder_scope.SetValue("deps", Value(nullptr, Value::LIST), nullptr);  \
    placeholder_scope.SetValue("public_deps", Value(nullptr, Value::LIST),     \
                               nullptr);                                       \
    placeholder_scope.SetValue("data_deps", Value(nullptr, Value::LIST),       \
                               nullptr);                                       \
    TargetGenerator::GenerateTarget(&placeholder_scope, invocation, args,      \
                                    "group", err);                             \
    return Value();                                                            \
  } else if (!functions::UpdateTheTemplate(invocation_scope.get(), invocation, \
                                           args, block, err, scope)) {         \
    return Value();                                                            \
  }

#include "../../gn/src/gn/template.cc"

#undef LATRODECTUS_GN_TEMPLATE_INVOKE
