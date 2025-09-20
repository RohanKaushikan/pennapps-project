"""
Configuration settings for the travel advisory scraping module.

This module provides centralized configuration for all scrapers,
allowing easy customization of scraping behavior.
"""

from typing import Dict, Any
from dataclasses import dataclass, field


@dataclass
class SourceConfig:
    """Configuration for a specific scraping source."""
    base_url: str
    rate_limit_delay: float = 1.0
    max_retries: int = 3
    retry_delay: float = 2.0
    timeout: int = 30
    user_agent: str = "TravelAdvisoryBot/1.0 (Travel Advisory Aggregator)"
    respect_robots_txt: bool = True
    headers: Dict[str, str] = field(default_factory=dict)
    enabled: bool = True

    def to_scraping_config(self):
        """Convert to ScrapingConfig object."""
        from .base_scraper import ScrapingConfig
        return ScrapingConfig(
            base_url=self.base_url,
            rate_limit_delay=self.rate_limit_delay,
            max_retries=self.max_retries,
            retry_delay=self.retry_delay,
            timeout=self.timeout,
            user_agent=self.user_agent,
            respect_robots_txt=self.respect_robots_txt,
            headers=self.headers
        )


class ScrapingModuleConfig:
    """Central configuration for the entire scraping module."""

    # Source configurations
    SOURCES = {
        'us_state_dept': SourceConfig(
            base_url="https://travel.state.gov",
            rate_limit_delay=1.5,  # US State Dept gets heavy traffic
            max_retries=3,
            timeout=30,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        ),

        'uk_foreign_office': SourceConfig(
            base_url="https://www.gov.uk",
            rate_limit_delay=1.0,  # UK gov sites are generally responsive
            max_retries=3,
            timeout=25,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-GB,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        ),

        'canada_travel': SourceConfig(
            base_url="https://travel.gc.ca",
            rate_limit_delay=1.2,  # Canadian sites prefer moderate pacing
            max_retries=3,
            timeout=25,
            headers={
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-CA,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
            }
        )
    }

    # Global scraping settings
    GLOBAL_SETTINGS = {
        # Maximum concurrent scrapers
        'max_concurrent_scrapers': 3,

        # Default user agent suffix (appended to source-specific agents)
        'user_agent_suffix': ' (+https://github.com/yourorg/travel-advisory-scraper)',

        # Content validation settings
        'min_content_length': 100,
        'max_content_length': 50000,

        # Change detection settings
        'content_hash_algorithm': 'sha256',
        'detect_risk_level_changes': True,
        'detect_content_changes': True,

        # Retry settings
        'default_max_retries': 3,
        'retry_exponential_base': 2,
        'max_retry_delay': 60,

        # Request settings
        'default_timeout': 30,
        'connection_timeout': 10,
        'read_timeout': 20,

        # Database settings
        'batch_size': 50,
        'commit_frequency': 10,

        # Logging settings
        'log_level': 'INFO',
        'log_requests': False,
        'log_responses': False,
        'log_parsing_details': False,

        # Error handling
        'continue_on_error': True,
        'max_consecutive_failures': 5,

        # Performance monitoring
        'track_performance_metrics': True,
        'performance_log_threshold': 5.0,  # seconds

        # Rate limiting
        'global_rate_limit': 0.5,  # minimum seconds between any requests
        'respect_retry_after': True,

        # Content processing
        'clean_html': True,
        'extract_metadata': True,
        'validate_urls': True,

        # Development/testing settings
        'dry_run': False,
        'sample_size': None,  # None = all, int = limit for testing
        'mock_responses': False,
    }

    @classmethod
    def get_source_config(cls, source_name: str) -> SourceConfig:
        """Get configuration for a specific source."""
        if source_name not in cls.SOURCES:
            raise ValueError(f"Unknown source: {source_name}")

        config = cls.SOURCES[source_name]

        # Add global user agent suffix if not already present
        suffix = cls.GLOBAL_SETTINGS['user_agent_suffix']
        if suffix and not config.user_agent.endswith(suffix):
            config.user_agent += suffix

        return config

    @classmethod
    def get_enabled_sources(cls) -> Dict[str, SourceConfig]:
        """Get all enabled source configurations."""
        return {
            name: config for name, config in cls.SOURCES.items()
            if config.enabled
        }

    @classmethod
    def is_source_enabled(cls, source_name: str) -> bool:
        """Check if a source is enabled."""
        return (source_name in cls.SOURCES and
                cls.SOURCES[source_name].enabled)

    @classmethod
    def get_global_setting(cls, key: str, default: Any = None) -> Any:
        """Get a global setting value."""
        return cls.GLOBAL_SETTINGS.get(key, default)

    @classmethod
    def update_source_config(cls, source_name: str, **kwargs) -> None:
        """Update configuration for a specific source."""
        if source_name not in cls.SOURCES:
            raise ValueError(f"Unknown source: {source_name}")

        config = cls.SOURCES[source_name]
        for key, value in kwargs.items():
            if hasattr(config, key):
                setattr(config, key, value)
            else:
                raise ValueError(f"Unknown config parameter: {key}")

    @classmethod
    def update_global_setting(cls, key: str, value: Any) -> None:
        """Update a global setting."""
        if key not in cls.GLOBAL_SETTINGS:
            raise ValueError(f"Unknown global setting: {key}")
        cls.GLOBAL_SETTINGS[key] = value

    @classmethod
    def enable_source(cls, source_name: str) -> None:
        """Enable a specific source."""
        if source_name in cls.SOURCES:
            cls.SOURCES[source_name].enabled = True

    @classmethod
    def disable_source(cls, source_name: str) -> None:
        """Disable a specific source."""
        if source_name in cls.SOURCES:
            cls.SOURCES[source_name].enabled = False

    @classmethod
    def get_config_summary(cls) -> Dict[str, Any]:
        """Get a summary of current configuration."""
        return {
            'sources': {
                name: {
                    'enabled': config.enabled,
                    'base_url': config.base_url,
                    'rate_limit_delay': config.rate_limit_delay,
                    'max_retries': config.max_retries,
                    'timeout': config.timeout
                }
                for name, config in cls.SOURCES.items()
            },
            'global_settings': dict(cls.GLOBAL_SETTINGS),
            'enabled_sources': list(cls.get_enabled_sources().keys())
        }


# Environment-specific configurations
class DevelopmentConfig(ScrapingModuleConfig):
    """Configuration for development environment."""

    GLOBAL_SETTINGS = {
        **ScrapingModuleConfig.GLOBAL_SETTINGS,
        'log_level': 'DEBUG',
        'log_requests': True,
        'log_parsing_details': True,
        'sample_size': 5,  # Limit scraping during development
        'max_concurrent_scrapers': 1,
    }


class ProductionConfig(ScrapingModuleConfig):
    """Configuration for production environment."""

    GLOBAL_SETTINGS = {
        **ScrapingModuleConfig.GLOBAL_SETTINGS,
        'log_level': 'INFO',
        'track_performance_metrics': True,
        'max_concurrent_scrapers': 5,
        'batch_size': 100,
    }


class TestingConfig(ScrapingModuleConfig):
    """Configuration for testing environment."""

    GLOBAL_SETTINGS = {
        **ScrapingModuleConfig.GLOBAL_SETTINGS,
        'dry_run': True,
        'mock_responses': True,
        'log_level': 'DEBUG',
        'sample_size': 2,
        'max_concurrent_scrapers': 1,
    }

    # Disable all sources by default in testing
    SOURCES = {
        name: SourceConfig(**{**config.__dict__, 'enabled': False})
        for name, config in ScrapingModuleConfig.SOURCES.items()
    }


def get_config(environment: str = 'development') -> ScrapingModuleConfig:
    """Get configuration for specified environment."""
    configs = {
        'development': DevelopmentConfig,
        'production': ProductionConfig,
        'testing': TestingConfig,
    }

    config_class = configs.get(environment, DevelopmentConfig)
    return config_class()