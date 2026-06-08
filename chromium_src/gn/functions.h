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

// disable_target
extern const char kDisableTarget[];
extern const char kDisableTarget_HelpShort[];
extern const char kDisableTarget_Help[];

Value RunDisableTarget(Scope* scope,
                       const FunctionCallNode* function,
                       const std::vector<Value>& args,
                       Err* err);

bool IsTargetDisabled(Scope* scope,
                      const FunctionCallNode* function,
                      const std::vector<Value>& args);

void ClearTargetScope(Scope* scope);

// disable_template_instance
extern const char kDisableTemplateInstance[];
extern const char kDisableTemplateInstance_HelpShort[];
extern const char kDisableTemplateInstance_Help[];

Value RunDisableTemplateInstance(Scope* scope,
                                 const FunctionCallNode* function,
                                 const std::vector<Value>& args,
                                 Err* err);

bool IsTemplateInstanceDisabled(Scope* scope,
                                const FunctionCallNode* function,
                                const std::vector<Value>& args);

// disable_file
extern const char kDisableFile[];
extern const char kDisableFile_HelpShort[];
extern const char kDisableFile_Help[];

Value RunDisableFile(Scope* scope,
                     const FunctionCallNode* function,
                     const std::vector<Value>& args,
                     Err* err);

// update_gni_file
extern const char kUpdateGniFile[];
extern const char kUpdateGniFile_HelpShort[];
extern const char kUpdateGniFile_Help[];

Value RunUpdateGniFile(Scope* scope,
                       const FunctionCallNode* function,
                       const std::vector<Value>& args,
                       BlockNode* block,
                       Err* err);

}  // namespace functions

#endif  // LATRODECTUS_CHROMIUM_SRC_GN_FUNCTIONS_H_
