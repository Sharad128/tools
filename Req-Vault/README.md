\# Req-Vault



A local, browser-based archive and viewer for raw HTTP requests and responses copied from Burp Suite or Caido.



Proxy history gets cleared, projects get deleted, and sessions get lost. Req-Vault keeps the full raw request and response so you can analyze them later.



\## Why I built it



During bug bounty hunts I kept losing interesting requests when proxy history was cleared. Exporting only URLs wasn't enough, because bugs like IDOR, auth issues and GraphQL problems depend on the full request (headers, tokens, body) and the exact response.



\## Features



\- Paste a raw request and its response, then save them with a title, tags and notes

\- Method, host, path and status are parsed automatically

\- Search across everything: hosts, headers, bodies, tags and notes

\- Side-by-side request and response view with copy and pretty-print JSON

\- Export and import as JSON for backups

\- Light and dark theme



\## Usage



1\. Open `index.html` in a browser.

2\. Click \*\*New\*\*, paste the raw request and response, and save.

3\. Use the search box to find saved items later.

4\. Use \*\*Export JSON\*\* regularly to back up your data.



\## Privacy and security



\- Everything is stored locally in your browser (IndexedDB). Nothing is sent to any server.

\- Saved requests often contain session cookies, tokens and program-confidential data. \*\*Never commit or share exported backups.\*\* The included `.gitignore` blocks `reqvault-backup-\*.json`.

\- Clearing your browser's site data deletes saved items, so keep exports as backups.

\- Pasting normalizes line endings (CRLF becomes LF), so keep the original bytes if you need exact wire-level fidelity.



\## Tech



Single-file vanilla HTML, CSS and JavaScript. No dependencies and no build step.

