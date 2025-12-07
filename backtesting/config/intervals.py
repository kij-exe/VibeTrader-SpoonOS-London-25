"""
Binance interval definitions and mappings.
"""

from enum import Enum
from typing import Dict


class BinanceInterval(str, Enum):
    """Supported Binance kline intervals."""
    MINUTE_1 = "1m"
    MINUTE_3 = "3m"
    MINUTE_5 = "5m"
    MINUTE_15 = "15m"
    MINUTE_30 = "30m"
    HOUR_1 = "1h"
    HOUR_2 = "2h"
    HOUR_4 = "4h"
    HOUR_6 = "6h"
    HOUR_8 = "8h"
    HOUR_12 = "12h"
    DAY_1 = "1d"
    DAY_3 = "3d"
    WEEK_1 = "1w"
    MONTH_1 = "1M"


# Interval to minutes mapping
INTERVAL_MINUTES: Dict[BinanceInterval, int] = {
    BinanceInterval.MINUTE_1: 1,
    BinanceInterval.MINUTE_3: 3,
    BinanceInterval.MINUTE_5: 5,
    BinanceInterval.MINUTE_15: 15,
    BinanceInterval.MINUTE_30: 30,
    BinanceInterval.HOUR_1: 60,
    BinanceInterval.HOUR_2: 120,
    BinanceInterval.HOUR_4: 240,
    BinanceInterval.HOUR_6: 360,
    BinanceInterval.HOUR_8: 480,
    BinanceInterval.HOUR_12: 720,
    BinanceInterval.DAY_1: 1440,
    BinanceInterval.DAY_3: 4320,
    BinanceInterval.WEEK_1: 10080,
    BinanceInterval.MONTH_1: 43200,  # Approximate
}


def get_interval_ms(interval: BinanceInterval) -> int:
    """Get interval duration in milliseconds."""
    return INTERVAL_MINUTES[interval] * 60 * 1000


def get_weight_for_limit(limit: int) -> int:
    """
    Get API weight for a given limit value.
    
    Based on Binance documentation:
    - [1, 100): weight 1
    - [100, 500): weight 2
    - [500, 1000]: weight 5
    - > 1000: weight 10
    """
    if limit < 100:
        return 1
    elif limit < 500:
        return 2
    elif limit <= 1000:
        return 5
    else:
        return 10


# Lean resolution mapping
INTERVAL_TO_LEAN_RESOLUTION: Dict[BinanceInterval, str] = {
    BinanceInterval.MINUTE_1: "Minute",
    BinanceInterval.MINUTE_5: "Minute",  # Will aggregate
    BinanceInterval.MINUTE_15: "Minute",
    BinanceInterval.MINUTE_30: "Minute",
    BinanceInterval.HOUR_1: "Hour",
    BinanceInterval.HOUR_4: "Hour",
    BinanceInterval.DAY_1: "Daily",
}
