# Connect services deliberately

The kit works with local files immediately. For current data, use an official MCP connection in your coding-agent host or call the service's API from a separately configured local script. The core tools do not install servers or contact your accounts.

## Common setup procedure

1. Choose the specific goal, source system, project/property and reporting window. Get the required owner permission. Prefer aggregate metrics over user-level records.
2. Find the provider's official connector documentation and verify package ownership. Pin the version if running a local server. Check which tools read, write, send, delete or spend. Give the host access only to required reads and approved resources.
3. Authenticate through the provider's OAuth flow when available. Keep tokens in the host credential store. For an API key, create the least-privileged key, reference it through an environment variable or secret store, and keep any local configuration outside Git. The ignored `.mcp.json` filename is available for hosts that use it, but each host has its own configuration format.
4. Run one bounded read and check account identity, region, resource ID, fields and date window. Confirm that writes and out-of-scope resources are denied or require a separate approval. A policy prompt alone cannot turn a broadly privileged connector into a read-only one.
5. Save the returned permitted result as a dated UTF-8 file in the private workspace. Record source URL/resource ID, actual event window, time queried, metric definitions, pagination/coverage, timezone and any missing data. Import that file with brain.py. The import timestamp records when it entered this workspace.
6. Reconcile the result against the service before using it in a decision. Respect rate limits and retry instructions. Mark partial results as partial. Revoke the service authorization and remove cached credentials when disconnecting.

Local environment variables do not require an .env file. If you use one, confirm Git ignores it and avoid asking an agent to print it. Use interactive secret entry or the OS credential store to avoid a token in terminal history. Never paste a live key in a chat or commit example values. See [privacy](privacy.md).

## PostHog

For an MCP connection, follow PostHog's official host-specific setup and sign in through OAuth. PostHog's connector exposes mutating capabilities as well as analytics reads, so inspect the available tools and restrict them for the second-brain task. Authentication/consent may grant more than a narrow reporting need. [Official MCP guide](https://posthog.com/docs/model-context-protocol)

For manual MCP setup, use the command for your installed host, then complete its OAuth prompt. These register a connection in your host configuration and should be run only when you want that account connected.

```sh
codex mcp add posthog --url https://mcp.posthog.com/mcp
```

```sh
claude mcp add --transport http posthog https://mcp.posthog.com/mcp -s user
```

Review tool permissions before the first data query. User-scoped host settings can apply to other projects, so check their effective scope. [PostHog's Codex instructions](https://posthog.com/docs/model-context-protocol/codex) · [Claude Code instructions](https://posthog.com/docs/model-context-protocol/claude-code)

For direct API use, create a personal API key restricted to the needed project and read scopes, such as `query:read`. A public project capture token is different from the private key used for analytics queries. Select the correct US, EU or self-hosted API region. Use the official query endpoint with a fixed aggregate request and a small reporting window. A POST used to execute a read-only analytics query still needs its body reviewed. [Scopes](https://posthog.com/docs/api/scopes) · [Query guide](https://posthog.com/docs/sql)

For a first check, ask for the total count of a known event in the last complete reporting week, with timezone and filters stated. Compare it with the dashboard. Avoid person profiles, recordings and raw identifiers. Save only the permitted aggregate and coverage notes under workspace, then import it. This release documents the connection procedure and uses host-managed connectors or your own API client.

## Google Analytics 4

Use the official Google Analytics MCP server guide for the host setup and supported authentication. Its current server setup requires Python 3.10+ and an isolated runner such as uvx or pipx, in addition to the core kit requirements. Enable the required Google APIs in your chosen Cloud project. Use `analytics.readonly` for reporting and follow the provider's current additional authentication requirements. The authorized user or service account also needs access to the intended GA4 property, typically the Viewer role for reads. Keep downloaded OAuth/client/service-account JSON and application-default credentials outside the repository. [Official MCP guide](https://developers.google.com/analytics/devguides/MCP)

For the Data API, follow the official `runReport` quickstart. For a first check use a single aggregate such as activeUsers for a complete date window, and compare it to an equivalent report in the UI. State the property ID, property timezone, filters, thresholding or sampling metadata, response limits and reporting freshness. An API result and a differently configured dashboard can legitimately differ. [Data API quickstart](https://developers.google.com/analytics/devguides/reporting/data/v1/quickstart)

When using a service account, grant access only to the needed property and follow your organization's credential policy. Prefer user OAuth or managed short-lived credentials where available. Restrict local key files with OS permissions. Revoke access in both Google Cloud and Analytics as appropriate when retiring the connection.

## File-only workflow

Export a scoped aggregate or permitted note, place it under the local workspace, add dates and coverage, and import it. This path works without MCP, an API client or live service authentication. It is a dated snapshot. An agent should state its coverage and avoid presenting it as a live query.

## Connection record

Fill [the connection record](../templates/connection.json) in the private workspace for each source. Record capability checks and the credential reference name only. It is an application record, not a native MCP configuration. It cannot enforce host tool permissions. Connections require a working host/provider setup and a successful scoped read before use in recurring reviews.
