"""
Suggestion-leak probing module.

Many GraphQL servers disable introspection but still return
"Did you mean ...?" style suggestions in error messages when an
unknown field name is queried, e.g.:

    Cannot query field "usre" on type "Query". Did you mean "user"?

This lets an auditor reconstruct fragments of the schema even with
introspection switched off. This module sends deliberately-invalid
field names at the root Query type and mines the resulting error
messages for suggested field names.
"""

import re

import requests

# Matches GraphQL's "Did you mean X, Y, or Z?" suggestion messages
# and captures the field/type names quoted inside it.
SUGGESTION_PATTERN = re.compile(r'Did you mean\s+((?:"[\w]+"[,\s]*(?:or\s+)?)+)\??', re.IGNORECASE)
QUOTED_NAME_PATTERN = re.compile(r'"([\w]+)"')

# Deliberately nonsense field names, unlikely to collide with real fields.
# Kept short and varied so the "Did you mean" edit-distance suggestions
# actually have real field names nearby to latch onto.
DEFAULT_PROBE_NAMES = [
    "zzzzzprobe",
    "aaaaaprobe",
    "____probe",
    "xprobex",
]


def _send_probe(endpoint, field_name, headers=None, timeout=10, verify_ssl=True):
    query = f"{{ {field_name} }}"
    resp = requests.post(
        endpoint,
        json={"query": query},
        headers=headers,
        timeout=timeout,
        verify=verify_ssl,
    )
    try:
        return resp.json()
    except ValueError:
        return {}


def _extract_suggestions(response_json):
    """Pull every suggested field/type name out of a GraphQL error response."""
    suggestions = set()
    for err in response_json.get("errors", []):
        message = err.get("message", "")
        match = SUGGESTION_PATTERN.search(message)
        if match:
            suggestions.update(QUOTED_NAME_PATTERN.findall(match.group(1)))
    return suggestions


def probe_suggestion_leak(endpoint, headers=None, timeout=10, verify_ssl=True,
                           probe_names=None):
    """
    Probe `endpoint` with nonsense field names and collect any field
    names leaked via "Did you mean" style suggestions.

    Returns a set of leaked field/type names. An empty set means
    either the server doesn't leak suggestions, or genuinely has no
    close-name matches for the probes used — pass your own
    `probe_names` (e.g. near-misses of names you already suspect)
    for a more targeted second pass.
    """
    headers = dict(headers or {})
    headers.setdefault("Content-Type", "application/json")

    leaked = set()
    for name in probe_names or DEFAULT_PROBE_NAMES:
        try:
            data = _send_probe(endpoint, name, headers, timeout, verify_ssl)
        except requests.RequestException:
            continue
        leaked.update(_extract_suggestions(data))
    return leaked
