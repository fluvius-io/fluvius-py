import ast, types
from simpleeval import SimpleEval

def enable_simpleeval_trace(ev):
    """
    Add a debug trace for every evaluation step inside SimpleEval.
    Ensures trace_log is always cleared before each top-level eval,
    so tracing is not cached and stale traces are not kept between evals.
    
    This function is idempotent - calling it multiple times on the same
    expression object will only patch it once.
    """

    # Check if already patched to avoid double-patching
    if hasattr(ev, '_trace_patched') and ev._trace_patched:
        return ev

    orig_eval_method = ev.eval
    orig__eval = ev._eval

    def pretty_trace_entry(entry, indent=0):
        # Use |-> to indicate tree-children, and indentation to show levels
        prefix = ""
        if indent > 0:
            prefix = "    " * (indent - 1) + "|-> "
        s = f"{prefix}{entry['type']}({entry['expr']!r}"
        if "result" in entry:
            s += f") => {entry['result']!r}"
        else:
            s += ")"
        if entry.get("children"):
            for child in entry["children"]:
                s += "\n" + pretty_trace_entry(child, indent + 1)
        return s


    def debug_eval_method(self, names=None):
        """
        Wrapper for eval() method that clears trace_log at the start of each call.
        This ensures that trace logs don't accumulate between multiple eval() calls
        on the same expression object.
        """
        # Clear trace log at the start of each eval() call
        ev._trace_log = []
        ev._trace_stack = []
        ev._debug_level = 0
        
        # Call the original eval method
        return orig_eval_method(names)

    def debug_eval(self, node):
        # Only clear trace for the outermost eval call.
        is_top_level = not hasattr(ev, "_trace_stack") or not ev._trace_stack
        if is_top_level:
            # Ensure trace_log is initialized (should already be cleared by eval() wrapper)
            if not hasattr(ev, "_trace_log"):
                ev._trace_log = []
            if not hasattr(ev, "_trace_stack"):
                ev._trace_stack = []
            if not hasattr(ev, "_debug_level"):
                ev._debug_level = 0

        typename = node.__class__.__name__
        expr = ast.get_source_segment(ev.expr, node)
        trace_entry = {
            "event": "eval",
            "type": typename,
            "expr": expr,
            "children": [],
            "level": getattr(ev, "_debug_level", 0)
        }

        # Attach as child in the tree
        if hasattr(ev, "_trace_stack") and ev._trace_stack:
            ev._trace_stack[-1]["children"].append(trace_entry)
        else:
            ev._trace_log.append(trace_entry)

        ev._trace_stack.append(trace_entry)
        ev._debug_level += 1
        value = orig__eval(node)
        ev._debug_level -= 1

        trace_entry["event"] = "result"
        trace_entry["result"] = value
        trace_entry["pretty"] = pretty_trace_entry(trace_entry)

        ev._trace_stack.pop()
        # For the root node, also clear the stack attribute after evaluation.
        if is_top_level and hasattr(ev, "_trace_stack"):
            del ev._trace_stack

        return value

    # Patch both eval() and _eval() methods
    ev.eval = types.MethodType(debug_eval_method, ev)
    ev._eval = types.MethodType(debug_eval, ev)
    ev._trace_patched = True  # Mark as patched
    return ev

def extract_trace_log(trace_log):
    """
    Consolidate the prettified traces from a list of trace logs.
    Returns a single string with all pretty traces joined.
    """
    if not trace_log:
        return ""
    pretties = []
    for entry in trace_log:
        pretty = entry.get("pretty")
        if pretty:
            pretties.append(pretty)
    return "\n\n".join(pretties)