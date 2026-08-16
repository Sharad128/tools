"""
GraphQL introspection module.

Sends the standard GraphQL introspection query to a target endpoint,
and parses the raw introspection response into a clean, readable
schema map: types, queries, mutations, and their arguments.
"""

import requests

# The standard full introspection query (per the GraphQL spec).
INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType { name }
    mutationType { name }
    subscriptionType { name }
    types {
      ...FullType
    }
  }
}

fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args {
      ...InputValue
    }
    type {
      ...TypeRef
    }
    isDeprecated
    deprecationReason
  }
  inputFields {
    ...InputValue
  }
  interfaces {
    ...TypeRef
  }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes {
    ...TypeRef
  }
}

fragment InputValue on __InputValue {
  name
  description
  type { ...TypeRef }
  defaultValue
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
            }
          }
        }
      }
    }
  }
}
"""


class IntrospectionError(Exception):
    """Raised when introspection fails, is disabled, or the response is unusable."""


def run_introspection(endpoint, headers=None, timeout=10, verify_ssl=True):
    """
    Send the introspection query to `endpoint`.

    Returns the parsed JSON response, or raises IntrospectionError
    if the request fails, the response isn't valid JSON, or the
    schema is missing (a strong signal introspection is disabled).
    """
    headers = dict(headers or {})
    headers.setdefault("Content-Type", "application/json")

    try:
        resp = requests.post(
            endpoint,
            json={"query": INTROSPECTION_QUERY, "operationName": "IntrospectionQuery"},
            headers=headers,
            timeout=timeout,
            verify=verify_ssl,
        )
    except requests.RequestException as exc:
        raise IntrospectionError(f"Request to {endpoint} failed: {exc}") from exc

    try:
        data = resp.json()
    except ValueError as exc:
        raise IntrospectionError(
            f"Response from {endpoint} was not valid JSON (status {resp.status_code})"
        ) from exc

    if not data.get("data", {}).get("__schema"):
        errors = data.get("errors")
        detail = f": {errors}" if errors else " (empty/blocked response)"
        raise IntrospectionError(f"No usable __schema in response from {endpoint}{detail}")

    return data


def _unwrap_type(type_ref):
    """
    Follow GraphQL's nested ofType chain (NON_NULL / LIST wrappers)
    down to the actual named type, and rebuild a compact display
    string like `[User!]!` or `String`.
    """
    if type_ref is None:
        return "Unknown"

    kind = type_ref.get("kind")
    name = type_ref.get("name")
    of_type = type_ref.get("ofType")

    if kind == "NON_NULL":
        return f"{_unwrap_type(of_type)}!"
    if kind == "LIST":
        return f"[{_unwrap_type(of_type)}]"
    return name or "Unknown"


def parse_schema(introspection_response):
    """
    Turn a raw introspection response into a clean schema map:

    {
        "query_type": "Query",
        "mutation_type": "Mutation",
        "types": {
            "User": {
                "kind": "OBJECT",
                "fields": {
                    "id": {"type": "ID!", "args": []},
                    "orders": {
                        "type": "[Order!]!",
                        "args": [{"name": "userId", "type": "ID!"}],
                    },
                },
            },
            ...
        },
        "queries": {...},     # fields on the root Query type
        "mutations": {...},   # fields on the root Mutation type
    }
    """
    schema = introspection_response["data"]["__schema"]

    query_type_name = (schema.get("queryType") or {}).get("name")
    mutation_type_name = (schema.get("mutationType") or {}).get("name")

    types = {}
    for t in schema.get("types", []):
        name = t.get("name")
        # Skip GraphQL's own introspection/meta types (__Type, __Schema, etc.)
        if not name or name.startswith("__"):
            continue

        fields = {}
        for f in t.get("fields") or []:
            fields[f["name"]] = {
                "type": _unwrap_type(f.get("type")),
                "args": [
                    {"name": a["name"], "type": _unwrap_type(a.get("type"))}
                    for a in f.get("args", [])
                ],
                "deprecated": f.get("isDeprecated", False),
            }

        types[name] = {
            "kind": t.get("kind"),
            "description": t.get("description"),
            "fields": fields,
        }

    return {
        "query_type": query_type_name,
        "mutation_type": mutation_type_name,
        "types": types,
        "queries": types.get(query_type_name, {}).get("fields", {}) if query_type_name else {},
        "mutations": types.get(mutation_type_name, {}).get("fields", {}) if mutation_type_name else {},
    }


def summarize_schema(schema_map):
    """
    Return a short human-readable summary string of a parsed schema
    for quick terminal output (counts + top-level query/mutation names).
    """
    lines = [
        f"Query type: {schema_map['query_type']}",
        f"Mutation type: {schema_map['mutation_type']}",
        f"Total types: {len(schema_map['types'])}",
        f"Queries: {len(schema_map['queries'])}",
        f"Mutations: {len(schema_map['mutations'])}",
        "",
        "Query fields:",
    ]
    for name, info in schema_map["queries"].items():
        args = ", ".join(f"{a['name']}: {a['type']}" for a in info["args"])
        lines.append(f"  {name}({args}): {info['type']}")

    lines.append("")
    lines.append("Mutation fields:")
    for name, info in schema_map["mutations"].items():
        args = ", ".join(f"{a['name']}: {a['type']}" for a in info["args"])
        lines.append(f"  {name}({args}): {info['type']}")

    return "\n".join(lines)
