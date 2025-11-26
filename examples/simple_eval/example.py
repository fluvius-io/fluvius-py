import ast, types
from simpleeval import SimpleEval

def enable_simpleeval_trace(ev):
    """
    Add a simple debug trace for every evaluation step inside SimpleEval.
    The trace_log will contain:
        - expr: the original expression string
        - explain: the evaluated expression with parameters substituted
        - failed_at: for any expression that ultimately evaluates to False, 
            a list of operator nodes that were the decisive point of failure
    """
    import ast

    orig_eval = ev._eval
    ev._trace_log = []
    ev._failed_ops = []

    def get_explain(expr_str, names):
        """Produce a string by substituting parameters actual values."""
        try:
            for k, v in names.items():
                expr_str = expr_str.replace(k, repr(v))
        except Exception:
            pass
        return expr_str

    def get_op_name(node):
        # Get operator AST kind as string for logging
        if isinstance(node, ast.BoolOp):
            return type(node.op).__name__
        if isinstance(node, ast.UnaryOp):
            return type(node.op).__name__
        if isinstance(node, ast.Compare):
            return "Compare(%s)" % type(node.ops[0]).__name__
        return type(node).__name__

    def debug_eval(self, node):
        # This stack stores (operator node, result) from all boolean operators
        if not hasattr(ev, "_eval_stack"):
            ev._eval_stack = []

        # Wrap evaluation of boolean/comparison nodes
        result = None

        # Handle BoolOp (and/or), UnaryOp (not), Compare specially
        if isinstance(node, ast.BoolOp):
            # Evaluate each value for 'and' / 'or'
            if isinstance(node.op, ast.And):
                for v in node.values:
                    vval = debug_eval(self, v)
                    if not vval:
                        # failure at this AND
                        ev._eval_stack.append(("and", ast.unparse(v)))
                        result = False
                        break
                else:
                    result = True
            elif isinstance(node.op, ast.Or):
                for v in node.values:
                    vval = debug_eval(self, v)
                    if vval:
                        result = True
                        break
                else:
                    ev._eval_stack.append(("or", "all-false"))
                    result = False
            else:
                result = orig_eval(node)
            return result
        elif isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            val = debug_eval(self, node.operand)
            result = not val
            if not result:
                ev._eval_stack.append(("not", ast.unparse(node)))
            return result
        elif isinstance(node, ast.Compare):
            # Only support single comparison
            left = debug_eval(self, node.left)
            right = debug_eval(self, node.comparators[0])
            op = node.ops[0]
            try:
                if isinstance(op, ast.Eq): cmp_result = left == right
                elif isinstance(op, ast.NotEq): cmp_result = left != right
                elif isinstance(op, ast.Lt): cmp_result = left < right
                elif isinstance(op, ast.LtE): cmp_result = left <= right
                elif isinstance(op, ast.Gt): cmp_result = left > right
                elif isinstance(op, ast.GtE): cmp_result = left >= right
                elif isinstance(op, ast.In): cmp_result = left in right
                elif isinstance(op, ast.NotIn): cmp_result = left not in right
                else: cmp_result = orig_eval(node)
            except Exception:
                cmp_result = orig_eval(node)
            if not cmp_result:
                ev._eval_stack.append(("compare", ast.unparse(node)))
            return cmp_result
        else:
            # Otherwise use standard
            return orig_eval(node)

    def traced_eval(self, node):
        # Only want the top-level call to fill trace_log
        if not hasattr(ev, "_traced_once"):
            ev._traced_once = True

            # Always reset the evaluation stack before evaluating exp
            if hasattr(ev, "_eval_stack"):
                ev._eval_stack.clear()
            else:
                ev._eval_stack = []

            try:
                value = debug_eval(self, node)
                trace_entry = {
                    "expr": ev.expr,
                    "explain": get_explain(ev.expr, ev.names),
                }
                if value is False and ev._eval_stack:
                    # Attach failures
                    trace_entry["failed_at"] = list(ev._eval_stack)
                ev._trace_log.append(trace_entry)
                return value
            except Exception as exc:
                trace_entry = {
                    "expr": ev.expr,
                    "explain": get_explain(ev.expr, ev.names),
                    "failed_at": list(ev._eval_stack)
                }
                ev._trace_log.append(trace_entry)
                raise
        return orig_eval(node)

    ev._eval = types.MethodType(traced_eval, ev)
    return ev


e = SimpleEval()

# Set a more complex expression
expression = (
    "(r_scope == 'SYS' or r_scope == 'ORG')"
    " or (g(r_sub, p_role, r_org) or (len(p_role) > 3 and custom_check(r_org)))"
    " and not blacklisted(r_sub)"
)
parsed = e.parse(expression)

e.functions = {
    "g": lambda s, r, o: s == "alice" and r == "admin" and o == "org1",
    "len": len,
    "custom_check": lambda org: org.startswith("org"),
    "blacklisted": lambda user: user == "bob",
}

# ---- Example 1: Should evaluate to True ----
params_true = {
    "r_scope": "SYS",
    "r_sub": "alice",
    "p_role": "admin",
    "r_org": "org1"
}
e.names = params_true
enable_simpleeval_trace(e)
result_true = e.eval(expression, previously_parsed=parsed)
print("Example 1 (Should be True):", result_true)
print("--------------------------------")
for entry in e._trace_log:
    print(entry)

# ---- Example 2: Should evaluate to False ----
params_false = {
    "r_scope": "ORG",
    "r_sub": "bob",        # blacklisted returns True, so expression should be False
    "p_role": "admin",
    "r_org": "org2"
}
e.names = params_false
enable_simpleeval_trace(e)
result_false = e.eval(expression, previously_parsed=parsed)
print("Example 2 (Should be False):", result_false)
print("--------------------------------")
for entry in e._trace_log:
    print(entry)