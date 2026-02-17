from datetime import datetime, timedelta, timezone
from typing import List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

openapi_tags = [
    {
        "name": "Health",
        "description": "Service health and readiness endpoints.",
    },
    {
        "name": "Metrics",
        "description": "Token usage and cost time-series metrics for dashboard visualization.",
    },
]


class TokensMetricPoint(BaseModel):
    """A single timeseries datapoint for token metrics."""

    timestamp: datetime = Field(..., description="UTC timestamp for this datapoint.")
    input_tokens: int = Field(..., ge=0, description="Number of input tokens for the time bucket.")
    output_tokens: int = Field(..., ge=0, description="Number of output tokens for the time bucket.")


class TokensMetricsResponse(BaseModel):
    """Response payload for token metrics."""

    points: List[TokensMetricPoint] = Field(..., description="Ordered list of timeseries datapoints.")


class CostMetricPoint(BaseModel):
    """A single timeseries datapoint for cost metrics."""

    timestamp: datetime = Field(..., description="UTC timestamp for this datapoint.")
    total_cost_usd: float = Field(..., ge=0, description="Total cost in USD for the time bucket.")


class CostMetricsResponse(BaseModel):
    """Response payload for cost metrics."""

    points: List[CostMetricPoint] = Field(..., description="Ordered list of timeseries datapoints.")


app = FastAPI(
    title="Token Metrics API",
    description=(
        "Backend API for serving input tokens, output tokens, and total cost data "
        "for a visualization dashboard."
    ),
    version="0.1.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _generate_demo_timestamps(num_points: int = 30) -> List[datetime]:
    """
    Generate a stable, ordered list of UTC timestamps for demo data.

    We intentionally keep this deterministic-ish (based on current day/hour boundaries)
    to avoid wildly changing charts on each refresh while still being "current".
    """
    now = datetime.now(timezone.utc)
    # Align to the hour for nicer-looking graphs
    aligned = now.replace(minute=0, second=0, microsecond=0)
    start = aligned - timedelta(hours=num_points - 1)
    return [start + timedelta(hours=i) for i in range(num_points)]


def _demo_tokens_series() -> List[TokensMetricPoint]:
    """Create demo token metrics (until a real database is wired in)."""
    ts = _generate_demo_timestamps(30)
    points: List[TokensMetricPoint] = []
    for idx, t in enumerate(ts):
        # Simple smooth-ish patterns with bounds
        input_tokens = 900 + (idx % 10) * 80 + (idx // 10) * 40
        output_tokens = 500 + (idx % 7) * 60 + (idx // 8) * 35
        points.append(
            TokensMetricPoint(
                timestamp=t,
                input_tokens=int(input_tokens),
                output_tokens=int(output_tokens),
            )
        )
    return points


def _demo_cost_series() -> List[CostMetricPoint]:
    """Create demo cost metrics (until a real database is wired in)."""
    ts = _generate_demo_timestamps(30)
    points: List[CostMetricPoint] = []
    # Roughly correlate with token volume for a believable curve
    token_points = _demo_tokens_series()
    for idx, t in enumerate(ts):
        total_tokens = token_points[idx].input_tokens + token_points[idx].output_tokens
        # A small per-1k token cost + slight trend
        total_cost = (total_tokens / 1000.0) * 0.015 + (idx * 0.002)
        points.append(CostMetricPoint(timestamp=t, total_cost_usd=round(float(total_cost), 4)))
    return points


@app.get(
    "/",
    tags=["Health"],
    summary="Health check",
    description="Simple health check endpoint used to verify the service is running.",
)
# PUBLIC_INTERFACE
def health_check():
    """Health check endpoint.

    Returns:
        JSON object: `{ "message": "Healthy" }`
    """
    return {"message": "Healthy"}


@app.get(
    "/metrics/tokens",
    response_model=TokensMetricsResponse,
    tags=["Metrics"],
    summary="Token metrics timeseries",
    description=(
        "Returns input and output token usage as a timeseries suitable for line graphs. "
        "Currently returns demo data."
    ),
    operation_id="get_token_metrics",
)
# PUBLIC_INTERFACE
def get_token_metrics() -> TokensMetricsResponse:
    """Get token metrics (input + output tokens) as a timeseries.

    Returns:
        TokensMetricsResponse: Ordered list of datapoints with timestamps in UTC.
    """
    return TokensMetricsResponse(points=_demo_tokens_series())


@app.get(
    "/metrics/cost",
    response_model=CostMetricsResponse,
    tags=["Metrics"],
    summary="Cost metrics timeseries",
    description=(
        "Returns total cost (USD) as a timeseries suitable for a line graph. "
        "Currently returns demo data."
    ),
    operation_id="get_cost_metrics",
)
# PUBLIC_INTERFACE
def get_cost_metrics() -> CostMetricsResponse:
    """Get total cost (USD) as a timeseries.

    Returns:
        CostMetricsResponse: Ordered list of datapoints with timestamps in UTC.
    """
    return CostMetricsResponse(points=_demo_cost_series())
