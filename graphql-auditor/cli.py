"""
CLI entry point for the GraphQL Security Auditor.

Usage:
    python cli.py --url https://target.com/graphql
    python cli.py --url https://target.com/graphql --header "Authorization: Bearer xyz"
"""

import argparse
import sys

from auditor.introspect import (
    IntrospectionError,
    run_introspection,
    parse_schema,
    summarize_schema,
)
from auditor.suggestion_leak import probe_suggestion_leak


def parse_headers(header_args):
    headers = {}
    for h in header_args or []:
        if ":" not in h:
            print(f"[!] Ignoring malformed header (expected 'Name: value'): {h}", file=sys.stderr)
            continue
        name, value = h.split(":", 1)
        headers[name.strip()] = value.strip()
    return headers


def main():
    parser = argparse.ArgumentParser(description="GraphQL Security Auditor")
    parser.add_argument("--url", required=True, help="Target GraphQL endpoint")
    parser.add_argument(
        "--header", action="append",
        help="Extra header, e.g. 'Authorization: Bearer xyz'. Repeatable.",
    )
    parser.add_argument("--no-verify-ssl", action="store_true", help="Disable TLS verification")
    args = parser.parse_args()

    headers = parse_headers(args.header)
    verify_ssl = not args.no_verify_ssl

    print(f"[*] Target: {args.url}")
    print("[*] Attempting introspection...")

    try:
        raw = run_introspection(args.url, headers=headers, verify_ssl=verify_ssl)
    except IntrospectionError as exc:
        print(f"[!] Introspection failed: {exc}")
        print("[*] Falling back to suggestion-leak probing...")
        leaked = probe_suggestion_leak(args.url, headers=headers, verify_ssl=verify_ssl)
        if leaked:
            print(f"[+] Leaked {len(leaked)} field/type name(s) via error suggestions:")
            for name in sorted(leaked):
                print(f"    - {name}")
        else:
            print("[-] No suggestion leaks found with the default probe set.")
        sys.exit(1)

    print("[+] Introspection succeeded.")
    schema_map = parse_schema(raw)
    print()
    print(summarize_schema(schema_map))


if __name__ == "__main__":
    main()
