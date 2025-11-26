from casbin.effect import Effector, effect_to_bool
from casbin.util import generate_g_function, util, generate_conditional_g_function
from casbin.core_enforcer import EnforceContext
from casbin import AsyncEnforcer

from fluvius.casbin import logger
from fluvius.casbin.helper import enable_simpleeval_trace, extract_trace_log


class FluviusEnforcer(AsyncEnforcer):
    def enforce_ex(self, *rvals):
            """decides whether a "subject" can access a "object" with the operation "action",
            input parameters are usually: (sub, obj, act).
            return judge result with reason
            """

            rtype = "r"
            ptype = "p"
            etype = "e"
            mtype = "m"

            if not self.enabled:
                return [True, [], []]

            functions = self.fm.get_functions()

            if "g" in self.model.keys():
                for key, ast in self.model["g"].items():
                    if len(self.rm_map) != 0:
                        functions[key] = generate_g_function(ast.rm)
                    if len(self.cond_rm_map) != 0:
                        functions[key] = generate_conditional_g_function(ast.cond_rm)

            if len(rvals) != 0:
                if isinstance(rvals[0], EnforceContext):
                    enforce_context = rvals[0]
                    rtype = enforce_context.rtype
                    ptype = enforce_context.ptype
                    etype = enforce_context.etype
                    mtype = enforce_context.mtype
                    rvals = rvals[1:]

            if "m" not in self.model.keys():
                raise RuntimeError("model is undefined")

            if "m" not in self.model["m"].keys():
                raise RuntimeError("model is undefined")

            r_tokens = self.model["r"][rtype].tokens
            p_tokens = self.model["p"][ptype].tokens

            if len(r_tokens) != len(rvals):
                raise RuntimeError("invalid request size")

            exp_string = self.model["m"][mtype].value
            exp_has_eval = util.has_eval(exp_string)
            if not exp_has_eval:
                expression = self._get_expression(exp_string, functions)

            policy_effects = set()

            r_parameters = dict(zip(r_tokens, rvals))

            policy_len = len(self.model["p"][ptype].policy)

            explain_index = -1
            explain_plist = []
            explain_trace = []
            if not 0 == policy_len:
                for i, pvals in enumerate(self.model["p"][ptype].policy):
                    if len(p_tokens) != len(pvals):
                        raise RuntimeError("invalid policy size")

                    p_parameters = dict(zip(p_tokens, pvals))
                    parameters = dict(r_parameters, **p_parameters)

                    if exp_has_eval:
                        rule_names = util.get_eval_value(exp_string)
                        rules = [util.escape_assertion(p_parameters[rule_name]) for rule_name in rule_names]
                        exp_with_rule = util.replace_eval(exp_string, rules)
                        expression = self._get_expression(exp_with_rule, functions)

                    enable_simpleeval_trace(expression)
                    result = expression.eval(parameters)

                    trace_log = expression._trace_log
                    explain_trace.append({"index": i, "result": result, "policy": self.model["p"][ptype].policy[i], "parameters": parameters, "detail": extract_trace_log(trace_log)})

                    if isinstance(result, bool):
                        if not result:
                            policy_effects.add(Effector.INDETERMINATE)
                            continue
                    elif isinstance(result, float):
                        if 0 == result:
                            policy_effects.add(Effector.INDETERMINATE)
                            continue
                    else:
                        raise RuntimeError("matcher result should be bool, int or float")

                    p_eft_key = ptype + "_eft"
                    if p_eft_key in parameters.keys():
                        eft = parameters[p_eft_key]
                        if "allow" == eft:
                            policy_effects.add(Effector.ALLOW)
                        elif "deny" == eft:
                            policy_effects.add(Effector.DENY)
                        else:
                            policy_effects.add(Effector.INDETERMINATE)
                    else:
                        policy_effects.add(Effector.ALLOW)

                    # if self.eft.intermediate_effect(policy_effects) != Effector.INDETERMINATE:
                    #     explain_index = i
                    #     explain_plist.append(i)
                    #     break

                    explain_plist.append(i)

            else:
                if exp_has_eval:
                    raise RuntimeError("please make sure rule exists in policy when using eval() in matcher")

                parameters = r_parameters.copy()

                for token in self.model["p"][ptype].tokens:
                    parameters[token] = ""

                result = expression.eval(parameters)

                if result:
                    policy_effects.add(Effector.ALLOW)
                else:
                    policy_effects.add(Effector.INDETERMINATE)

            final_effect = self.eft.final_effect(policy_effects)
            result = effect_to_bool(final_effect)

            # Log request.

            req_str = "Request: "
            req_str = req_str + ", ".join([str(v) for v in rvals])

            req_str = req_str + " ---> %s" % result
            if result:
                self.logger.info(req_str)
            else:
                # leaving this in warning for now, if it's very noise this can be changed to info or debug,
                # or change the log level
                self.logger.warning(req_str)

            # explain_rule = []
            # if explain_index != -1 and explain_index < policy_len:
            #     explain_rule = self.model["p"][ptype].policy[explain_index]
            
            # return result, explain_rule
            
            explain_rule = []
            for index in explain_plist:
                if index != -1 and index < policy_len:
                    explain_rule.append(self.model["p"][ptype].policy[index])
            return result, explain_rule, explain_trace