# Health API MCP server

This FastMCP server exposes the health API's read-only endpoints as MCP tools:

- `list_health_metrics`
- `get_health_metrics`
- `get_health_summary`

## Tool parameters

### `list_health_metrics`

Takes no parameters. It returns the exact metric names available in the database.
Use it before filtering `get_health_metrics`; metric names are data-driven rather
than a fixed enum.

### `get_health_metrics`

- `from_` (required): inclusive ISO 8601 start timestamp, such as
  `2026-10-01T00:00:00+02:00`.
- `to` (required): inclusive ISO 8601 end timestamp. It must be later than
  `from_`, and the requested range cannot exceed 30 days. Both timestamps must
  include a timezone or UTC offset.
- `metrics` (optional): a list of exact names returned by `list_health_metrics`,
  such as `["step_count", "heart_rate"]`. Omit it or pass `null` to request all
  metrics.

The MCP tool converts `metrics` to the comma-separated query parameter expected by
`GET /api/v1/health/`.

### `get_health_summary`

- `end_date` (required): a reference date in `YYYY-MM-DD` format.
- `summary_type` (optional, default `week`): one of the following exact values:

| Value | Period selected |
| --- | --- |
| `week` | Seven days ending on and including `end_date` |
| `twoweeks` | Fourteen days ending on and including `end_date` |
| `thirtydays` | Thirty days ending on and including `end_date` |
| `month` | The entire calendar month containing `end_date` |

For example, `end_date=2026-10-17` with `summary_type=week` selects October 11–17.
With `summary_type=month`, the same date selects October 1–31; in this case the
parameter is a month reference, not literally the period's final day.

The summary combines recovery, sleep, training, energy, fitness, body, and
nutrition data. Its daily arrays correspond to the period described by the
response's `meta.period_start`, `meta.period_end`, and `meta.days` fields.

The server listens at `http://0.0.0.0:8000/mcp`. Configure its upstream with:

- `HEALTH_API_BASE_URL` (default: `http://host.docker.internal:8000`)
- `HEALTH_API_TIMEOUT_SECONDS` (default: `30`)

From the repository root, provide the tunnel credentials and start both services:

```shell
export CONTROL_PLANE_API_KEY="..."
export CONTROL_PLANE_TUNNEL_ID="..."
docker compose up --build
```

If the health API is not listening on the host at port 8000, set
`HEALTH_API_BASE_URL` to an address reachable from the MCP container.

## Server deployment

The root `docker-compose.yaml` is a pull-only deployment stack containing
InfluxDB 3 Core, an OpenTelemetry collector, the published health API and MCP
server images, and the OpenAI tunnel client. Copy `.env.example` to `.env`, fill
in the tunnel credentials and any InfluxDB token, then run:

```shell
docker compose pull
docker compose up -d
```

On a fresh InfluxDB volume, create the configured database once after InfluxDB
starts (the default name is `health`):

```shell
docker compose exec influxdb influxdb3 create database health
```

The health API binds to `127.0.0.1:8000` by default because its ingest endpoints
do not implement authentication. Put it behind an authenticated reverse proxy or
explicitly change `HEALTH_API_BIND_ADDRESS` if it must accept remote ingestion.
