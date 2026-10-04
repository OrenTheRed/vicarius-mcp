"""Be forgiving about how a client writes tool arguments, and say clearly what is wrong when it is not.

Different models and MCP clients encode arguments differently. Some send a JSON object as a string
("{\\"severityIn\\": [\\"CRITICAL\\"]}") where the tool wants an object, or write the word "null" for an
empty value. This middleware fixes those cases in one place, for every tool, using the tool's own
schema. It never reinterprets a value that the schema allows as a string, with one exception: for
the `tenant` argument, the text "null" or "none" means "no tenant given", so the default tenant is used.

When an argument is still wrong, the error names the problem and the fix in a sentence, instead of
a validation dump, so an agent can correct the call on its next try.
"""

from __future__ import annotations

import json

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware

_MAX_SHOWN = 60  # characters of a bad value shown in an error


def _types(spec: dict) -> set:
    """JSON types a parameter accepts. An empty set means 'unknown, leave it alone'."""
    if not isinstance(spec, dict) or "$ref" in spec:
        return set()
    found = set()
    declared = spec.get("type")
    if isinstance(declared, str):
        found.add(declared)
    elif isinstance(declared, list):
        found.update(t for t in declared if isinstance(t, str))
    for key in ("anyOf", "oneOf"):
        for option in spec.get(key, []):
            sub = _types(option)
            if not sub:
                return set()  # an option we cannot read: do not guess
            found |= sub
    return found


def coerce_arguments(arguments: dict, schema: dict) -> dict:
    """A copy of `arguments` where JSON written as text becomes the object or array the schema wants."""
    properties = (schema or {}).get("properties", {})
    fixed = dict(arguments)
    for name, value in arguments.items():
        if not isinstance(value, str) or name not in properties:
            continue
        types = _types(properties[name])
        text = value.strip()
        if name == "tenant" and "null" in types and text.lower() in ("null", "none"):
            fixed[name] = None  # a model's way of saying "no tenant": use the default one
            continue
        if not types or "string" in types:
            continue  # a plain string is allowed here: never reinterpret it
        if "null" in types and text.lower() in ("null", "none"):
            fixed[name] = None
        elif "object" in types and text.startswith("{") or "array" in types and text.startswith("["):
            try:
                parsed = json.loads(text)
            except ValueError:
                continue
            wanted = (dict,) if text.startswith("{") else (list,)
            if isinstance(parsed, wanted[0]) and ("object" in types if wanted[0] is dict else "array" in types):
                fixed[name] = parsed
    return fixed


def _shown(value) -> str:
    text = value if isinstance(value, str) else json.dumps(value, default=str)
    return text if len(text) <= _MAX_SHOWN else text[:_MAX_SHOWN] + "..."


def find_problems(tool: str, arguments: dict, schema: dict) -> list:
    """Sentences for the arguments the tool would reject anyway: names it does not have, required
    ones that are missing, and text or numbers where an object or an array is needed."""
    properties = (schema or {}).get("properties", {})
    parameters = ", ".join(sorted(properties))
    problems = []
    for name in arguments:
        if name not in properties:
            problems.append(f"`{name}` is not a parameter of {tool}. Its parameters are: {parameters}. "
                            "Filters belong inside the `params` object, not at the top level.")
    for name in (schema or {}).get("required", []):
        if name not in arguments:
            problems.append(f"`{name}` is required.")
    for name, value in arguments.items():
        types = _types(properties.get(name, {}))
        if not types:
            continue
        if types <= {"object", "null"} and value is not None and not isinstance(value, dict):
            problems.append(f"`{name}` must be a JSON object such as {{\"key\": \"value\"}}. Got: {_shown(value)}.")
        elif types <= {"array", "null"} and value is not None and not isinstance(value, list):
            problems.append(f"`{name}` must be a JSON array such as [\"a\", \"b\"]. Got: {_shown(value)}.")
    return problems


class LenientArguments(Middleware):
    async def on_call_tool(self, context, call_next):
        name = context.message.name
        try:
            tool = await context.fastmcp_context.fastmcp.get_tool(name)
        except Exception:
            tool = None
        if tool is None:
            return await call_next(context)  # unknown tool: let the server report it as usual
        schema = tool.parameters or {}
        arguments = coerce_arguments(context.message.arguments or {}, schema)
        context.message.arguments = arguments
        problems = find_problems(name, arguments, schema)
        if problems:
            raise ToolError(f"Invalid arguments for {name}. " + " ".join(problems) + " Fix the arguments and call the tool again.")
        return await call_next(context)
