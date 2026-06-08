#ifndef LATRODECTUS_CHROMIUM_SRC_GN_FUNCTIONS_H_
#define LATRODECTUS_CHROMIUM_SRC_GN_FUNCTIONS_H_

#include "../../gn/src/gn/functions.h"

namespace functions {

// update_target
extern const char kUpdateTarget[];
extern const char kUpdateTarget_HelpShort[];
extern const char kUpdateTarget_Help[];

Value RunUpdateTarget(Scope* scope,
                      const FunctionCallNode* function,
                      const std::vector<Value>& args,
                      BlockNode* block,
                      Err* err);

bool UpdateTheTarget(Scope* scope,
                     const FunctionCallNode* function,
                     const std::vector<Value>& args,
                     BlockNode* block,
                     Err* err);

// update_template_instance
extern const char kUpdateTemplate[];
extern const char kUpdateTemplate_HelpShort[];
extern const char kUpdateTemplate_Help[];

Value RunUpdateTemplate(Scope* scope,
                        const FunctionCallNode* function,
                        const std::vector<Value>& args,
                        BlockNode* block,
                        Err* err);

bool UpdateTheTemplate(Scope* scope,
                       const FunctionCallNode* function,
                       const std::vector<Value>& args,
                       BlockNode* block,
                       Err* err,
                       Scope* function_scope);

}  // namespace functions

#endif  // LATRODECTUS_CHROMIUM_SRC_GN_FUNCTIONS_H_
