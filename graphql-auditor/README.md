# GraphQL Security Auditor

A CLI tool for auditing GraphQL endpoints during security testing / bug bounty
recon. Built to automate the parts of GraphQL recon that are tedious to do by
hand, while leaving actual exploitation to the researcher.

## Why this exists

Most public GraphQL tooling either (a) just dumps the introspected schema and
stops, or (b) assumes introspection is enabled, which it usually isn't on
anything past a staging environment. This tool is built around the reality
that introspection is often locked down, and focuses on what's still possible
when it is.

## Features (v1)

- **Introspection** — runs the full standard introspection query and parses
  the response into a clean, readable schema map (types, queries, mutations,
  arguments).
- **Suggestion-leak probing** — when introspection is disabled, probes the
  endpoint with deliberately-invalid field names and mines the server's
  `Did you mean "x"?` error messages to reconstruct fragments of the schema
  anyway.
- **Clean CLI output** — human-readable summary of every query/mutation and
  its arguments, so you can immediately spot ID-like arguments worth manual
  IDOR/BOLA testing.

## Planned (next)

- Misconfig checks: batching/aliasing DoS, missing query-depth limits
- Automatic flagging of ID-like arguments as IDOR/BOLA testing candidates
- Two-account diffing: replay flagged queries as two identities and diff
  responses to surface likely broken object-level authorization
- Markdown/JSON report output

## Installation

```bash
git clone https://github.com/Sharad128/tools.git
cd tools/graphql-auditor
pip install -r requirements.txt
```

## Usage

```bash
python cli.py --url https://target.com/graphql
```

With auth or custom headers:

```bash
python cli.py --url https://target.com/graphql --header "Authorization: Bearer <token>"
```

Skip TLS verification (self-signed certs, internal targets):

```bash
python cli.py --url https://target.com/graphql --no-verify-ssl
```

### Example output (introspection enabled)

```
[*] Target: https://target.com/graphql
[*] Attempting introspection...
[+] Introspection succeeded.

Query type: Query
Mutation type: Mutation
Total types: 42
Queries: 8
Mutations: 5

Query fields:
  user(id: ID!): User
  orders(userId: ID!): [Order!]!
  ...
```

### Example output (introspection disabled, falls back automatically)

```
[*] Target: https://target.com/graphql
[*] Attempting introspection...
[!] Introspection failed: No usable __schema in response ...
[*] Falling back to suggestion-leak probing...
[+] Leaked 3 field/type name(s) via error suggestions:
    - order
    - user
    - userProfile
```

## Testing

```bash
python -m unittest discover tests
```

## Legal

Only run this against targets you own or have explicit written authorization
to test (e.g. an active bug bounty program's in-scope assets). Unauthorized
access to computer systems is illegal in most jurisdictions.

## License

MIT
