# Monitoring and endpoint diagnostics

The original Home check still follows `https://yunle.fun` to
`https://www.yunle.fun/`; the permanent redirect is expected. Home and App
alert rules and request timeouts are unchanged.

Uptime checks are requested at minutes 27 and 57 UTC, preserving the
30-minute cadence while avoiding the busiest top-of-hour scheduling period.
GitHub schedule events can be delayed or dropped. Check Actions run history
for monitoring freshness; `history/*.yml` lastUpdated only changes when
Upptime writes a status or response-time update. A green workflow conclusion
means the monitor ran successfully, not that every endpoint is healthy.

Run **Endpoint diagnostics** manually to compare the apex redirect, direct
www response, complete redirect chain, and App in one time window. It logs
remote IPs, DNS/TCP/TLS/TTFB/total timing milestones and allowlisted response
headers. It uses the monitor's 30-second connect and 60-second request
timeouts, verifies TLS, and does not change incident state or send messages.
Record the runner region from the setup logs before comparing locations.

Generated workflows are owned by Upptime. Edit `.upptimerc.yml` for schedules
and let Setup CI regenerate them; do not manually upgrade their dependencies
only to have the next template update revert them. The custom diagnostic
workflow uses checkout v7.0.1 with credential persistence disabled.

Dependencies reviewed on 2026-10-02:

- Upptime v1.44.1 is already the latest stable release, including js-yaml 4.3.2.
- The generated checkout v6 / create-github-app-token v3 / setup-node v6
  major tags receive compatible upstream updates. Their versions are managed
  by the Upptime template rather than a local package manifest.
- checkout v7.0.1 uses Node 24 and adds safer PR defaults and dependency fixes.
  The manual diagnostic workflow uses hosted Ubuntu runners and no PR code,
  so the new defaults require no security opt-out or extra permissions.

References: [Upptime release](https://github.com/upptime/uptime-monitor/releases/tag/v1.44.1),
[checkout release](https://github.com/actions/checkout/releases/tag/v7.0.1),
[checkout migration](https://github.com/actions/checkout/blob/v7.0.1/README.md),
[GitHub schedule limitations](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).
