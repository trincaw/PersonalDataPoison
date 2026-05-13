from __future__ import annotations

from typing import Any

CONFIG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "general": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string"},
                "data_dir": {"type": "string"},
                "log_level": {"type": "string", "enum": ["DEBUG", "INFO", "WARNING", "ERROR"]},
            },
        },
        "identity": {
            "type": "object",
            "properties": {
                "default_locale": {"type": "string"},
                "pool_size": {"type": "integer", "minimum": 1},
                "rotation_policy": {
                    "type": "string",
                    "enum": ["round_robin", "random", "scored"],
                },
            },
        },
        "browser": {
            "type": "object",
            "properties": {
                "browser_type": {
                    "type": "string",
                    "enum": ["chromium", "firefox", "webkit"],
                },
                "headless": {"type": "boolean"},
                "block_trackers": {"type": "boolean"},
                "profile_storage_dir": {"type": "string"},
            },
        },
        "network": {
            "type": "object",
            "properties": {
                "proxy": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "proxies": {
                            "type": "array",
                            "items": {"type": "string"},
                        },
                        "max_fails": {"type": "integer", "minimum": 1},
                    },
                },
                "dns": {
                    "type": "object",
                    "properties": {
                        "use_doh": {"type": "boolean"},
                        "rotate": {"type": "boolean"},
                    },
                },
            },
        },
        "timing": {
            "type": "object",
            "properties": {
                "circadian": {
                    "type": "object",
                    "properties": {
                        "wake_hour": {"type": "integer", "minimum": 0, "maximum": 23},
                        "sleep_hour": {"type": "integer", "minimum": 0, "maximum": 23},
                        "peak_hour": {"type": "integer", "minimum": 0, "maximum": 23},
                    },
                },
                "inter_page_mean": {"type": "number", "minimum": 0.1},
                "inter_page_sigma": {"type": "number", "minimum": 0.0},
                "inter_session_mean": {"type": "number", "minimum": 1.0},
                "inter_session_sigma": {"type": "number", "minimum": 0.0},
            },
        },
        "session": {
            "type": "object",
            "properties": {
                "min_pages": {"type": "integer", "minimum": 1},
                "max_pages": {"type": "integer", "minimum": 1},
                "max_sessions": {"type": "integer", "minimum": 0},
            },
        },
        "navigation": {
            "type": "object",
            "properties": {
                "seed_urls": {
                    "type": "array",
                    "items": {"type": "string", "format": "uri"},
                },
                "follow_links": {"type": "boolean"},
                "same_domain_probability": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "storage": {
            "type": "object",
            "properties": {
                "database_path": {"type": "string"},
                "identities_dir": {"type": "string"},
            },
        },
        "plugins": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
}
