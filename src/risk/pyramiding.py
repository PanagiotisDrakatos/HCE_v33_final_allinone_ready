from dataclasses import dataclass


@dataclass
class PyramidingConfig:
    """Configuration for pyramiding position sizing."""

    max_layers: int = 3
    risk_neutral: bool = True


def next_size(current_layers: int, base_size: float, cfg: PyramidingConfig) -> float:
    """Return the size of the next layer for a pyramiding strategy.

    If ``risk_neutral`` is enabled we keep the size constant. Otherwise we gradually
    increase the position size following a simple geometric progression.
    """

    if current_layers >= cfg.max_layers:
        return 0.0

    if cfg.risk_neutral:
        return base_size

    return base_size * (1.0 + 0.25 * current_layers)
