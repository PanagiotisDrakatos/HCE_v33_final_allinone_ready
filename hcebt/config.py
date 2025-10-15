from pydantic import BaseModel, Field
from typing import Literal, Optional

SlipMode = Literal["fixed_ticks","bps","pct_spread","hybrid"]

class FillConfig(BaseModel):
    slip_mode: SlipMode = "bps"
    ticks: float = 1.0
    bps: float = 2.0
    pct_spread: float = 0.5
    hybrid_weight: float = 0.5
    bid_ask_aware: bool = True
    seed: int = 42

class BatchConfig(BaseModel):
    backend: Literal["none","clickhouse","timescale"] = "none"
    batch_size: int = 5000
    flush_interval_ms: int = 500
    queue_max_batches: int = 200
    clickhouse_url: str = "http://localhost:8123"
    timescale_dsn: str = "postgresql://postgres:postgres@localhost:5432/hce"
    table: str = "market_signals"

class RunConfig(BaseModel):
    run_id: str
    strat_id: str = "default"
    commit_sha: Optional[str] = None
    fill: FillConfig = Field(default_factory=FillConfig)
    batch: BatchConfig = Field(default_factory=BatchConfig)
