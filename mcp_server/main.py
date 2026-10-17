"""FastMCP tools for the read-only health API endpoints."""

import os
from datetime import date, datetime
from typing import Annotated, Any, Literal

import httpx
from fastmcp import FastMCP
from fastmcp.exceptions import ToolError
from pydantic import Field

mcp = FastMCP(
    name="Health API MCP Server",
    instructions=(
        "Read health measurements and summaries from the configured health API. "
        "All tools are read-only."
    ),
)

HEALTH_API_BASE_URL = os.getenv(
    "HEALTH_API_BASE_URL", "http://host.docker.internal:8000"
).rstrip("/")
HEALTH_API_TIMEOUT_SECONDS = float(os.getenv("HEALTH_API_TIMEOUT_SECONDS", "30"))


async def _get(path: str, params: dict[str, Any] | None = None) -> Any:
    """Call a health API reader endpoint and normalize failures for MCP clients."""
    try:
        async with httpx.AsyncClient(
            base_url=HEALTH_API_BASE_URL,
            timeout=HEALTH_API_TIMEOUT_SECONDS,
            headers={"User-Agent": "health-api-mcp/0.1.0"},
        ) as client:
            response = await client.get(path, params=params)
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as exc:
        try:
            detail = exc.response.json().get("detail", exc.response.text)
        except (ValueError, AttributeError):
            detail = exc.response.text
        raise ToolError(
            f"Health API returned {exc.response.status_code}: {detail}"
        ) from exc
    except httpx.TimeoutException as exc:
        raise ToolError("Health API request timed out") from exc
    except httpx.HTTPError as exc:
        raise ToolError(f"Could not reach the health API: {exc}") from exc
    except ValueError as exc:
        raise ToolError("Health API returned invalid JSON") from exc


@mcp.tool
async def list_health_metrics() -> dict[str, Any]:
    """List the metric names currently available in the health database."""
    return await _get("/api/v1/health/metrics")


@mcp.tool
async def get_health_metrics(
    from_: Annotated[
        datetime,
        Field(
            description=(
                "Inclusive start timestamp in ISO 8601 format, for example "
                "2026-10-01T00:00:00+02:00. Include a UTC offset when possible."
            )
        ),
    ],
    to: Annotated[
        datetime,
        Field(
            description=(
                "Inclusive end timestamp in ISO 8601 format, for example "
                "2026-10-17T23:59:59+02:00. Must be later than from_; the maximum "
                "range is 30 days."
            )
        ),
    ],
    metrics: Annotated[
        list[str] | None,
        Field(
            description=(
                "Optional exact metric-name filters. Use list_health_metrics first "
                "to discover valid names. Omit or pass null to request all metrics."
            )
        ),
    ] = None,
) -> dict[str, Any]:
    """Read raw health metrics over an inclusive time range.

    Args:
        from_: Start of the requested range, including timezone when applicable.
        to: End of the requested range, including timezone when applicable.
        metrics: Optional metric names to filter by; omit to return all metrics.
    """
    if from_.tzinfo is None or to.tzinfo is None:
        raise ToolError("from_ and to must include a timezone or UTC offset")
    if from_ >= to:
        raise ToolError("from_ must be earlier than to")
    if (to - from_).total_seconds() > 30 * 24 * 60 * 60:
        raise ToolError("the requested time range cannot exceed 30 days")

    params = {"from": from_.isoformat(), "to": to.isoformat()}
    if metrics:
        params["metrics"] = ",".join(metrics)
    return await _get("/api/v1/health/", params=params)


@mcp.tool
async def get_health_summary(
    end_date: Annotated[
        date,
        Field(
            description=(
                "Reference date in YYYY-MM-DD format. It is the inclusive period end "
                "for week, twoweeks, and thirtydays. For month, any date in the "
                "desired calendar month selects that entire month."
            )
        ),
    ],
    summary_type: Annotated[
        Literal["week", "twoweeks", "thirtydays", "month"],
        Field(
            description=(
                "Summary window: week is 7 days ending on end_date; twoweeks is 14 "
                "days; thirtydays is 30 days; month is the complete calendar month "
                "containing end_date."
            )
        ),
    ] = "week",
) -> dict[str, Any]:
    """Read an aggregated recovery, sleep, training, and nutrition summary.

    Args:
        end_date: Reference date used to calculate the requested period.
        summary_type: One of week, twoweeks, thirtydays, or month. The rolling periods
            include end_date. Month returns the whole month containing end_date,
            including dates after it when end_date is not the month's final day.
    """
    return await _get(
        "/api/v1/health/summary",
        params={"end_date": end_date.isoformat(), "summary_type": summary_type},
    )


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8000, path="/mcp")
