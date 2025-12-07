"""
Global settings for the backtesting system.

Uses environment variables with sensible defaults.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
from functools import lru_cache


@dataclass
class BinanceConfig:
    """Binance API configuration."""
    base_url: str = "https://api.binance.com"
    klines_endpoint: str = "/api/v3/klines"
    max_limit: int = 1500
    default_limit: int = 1000
    # Rate limiting: requests per minute
    rate_limit_requests: int = 1200
    rate_limit_weight: int = 6000  # Weight limit per minute
    user_agent: str = "Mozilla/5.0"


@dataclass
class LeanConfig:
    """Lean QuantConnect configuration."""
    # Docker image for Lean CLI
    docker_image: str = "quantconnect/lean:latest"
    # Timeout for backtest execution (seconds)
    execution_timeout: int = 300
    # Default starting capital
    default_capital: float = 100000.0
    # Default currency
    default_currency: str = "USD"


@dataclass
class PathConfig:
    """Path configuration for data storage."""
    base_dir: Path = field(default_factory=lambda: Path(__file__).parent.parent.parent / "backtesting")
    
    @property
    def raw_data_dir(self) -> Path:
        """Directory for raw Binance JSON data."""
        return self.base_dir / "data_storage" / "raw"
    
    @property
    def lean_data_dir(self) -> Path:
        """Directory for Lean-formatted data."""
        return self.base_dir / "data_storage" / "lean"
    
    @property
    def strategies_dir(self) -> Path:
        """Directory for strategy files."""
        return self.base_dir / "strategies"
    
    @property
    def results_dir(self) -> Path:
        """Directory for backtest results."""
        return self.base_dir / "results"
    
    @property
    def logs_dir(self) -> Path:
        """Directory for logs."""
        return self.base_dir / "logs"
    
    def ensure_dirs(self) -> None:
        """Create all required directories."""
        for dir_path in [
            self.raw_data_dir,
            self.lean_data_dir,
            self.strategies_dir,
            self.results_dir,
            self.logs_dir,
        ]:
            dir_path.mkdir(parents=True, exist_ok=True)


@dataclass
class Settings:
    """Main settings container."""
    binance: BinanceConfig = field(default_factory=BinanceConfig)
    lean: LeanConfig = field(default_factory=LeanConfig)
    paths: PathConfig = field(default_factory=PathConfig)
    
    # Debug mode
    debug: bool = False
    
    def __post_init__(self):
        """Load from environment variables."""
        # Binance settings
        if base_url := os.getenv("BINANCE_BASE_URL"):
            self.binance.base_url = base_url
        
        # Lean settings
        if docker_image := os.getenv("LEAN_DOCKER_IMAGE"):
            self.lean.docker_image = docker_image
        if timeout := os.getenv("LEAN_EXECUTION_TIMEOUT"):
            self.lean.execution_timeout = int(timeout)
        if capital := os.getenv("LEAN_DEFAULT_CAPITAL"):
            self.lean.default_capital = float(capital)
        
        # Debug
        self.debug = os.getenv("DEBUG", "").lower() in ("true", "1", "yes")
        
        # Ensure directories exist
        self.paths.ensure_dirs()


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
