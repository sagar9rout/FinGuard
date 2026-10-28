from __future__ import annotations

import pytest

from app.core.config import ConfigError, Settings, settings_from_environ


def test_defaults_are_loopback_only_with_no_cors():
    s = Settings()
    assert s.host == "127.0.0.1" and s.port == 8000 and s.cors_origins == () and s.max_body_bytes == 1_048_576


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.5", "10.0.0.1", "example.com", ""])
def test_non_loopback_bind_addresses_are_rejected(host):
    with pytest.raises(ConfigError):
        Settings(host=host)


@pytest.mark.parametrize("host", ["127.0.0.1", "::1", "localhost", "127.0.0.2"])
def test_loopback_bind_addresses_are_accepted(host):
    assert Settings(host=host).host == host


@pytest.mark.parametrize("origin", ["*", "null", "http://localhost:5173/", "http://localhost:5173/app", "https://evil.example", "http://192.168.1.2:5173", "ftp://localhost", "localhost:5173", "http://localhost:99999"])
def test_bad_or_non_loopback_origins_are_rejected(origin):
    with pytest.raises(ConfigError):
        Settings(cors_origins=(origin,))


@pytest.mark.parametrize("origin", ["http://localhost:5173", "http://127.0.0.1:5173", "https://localhost:5173", "http://[::1]:5173"])
def test_exact_loopback_origins_are_accepted(origin):
    assert Settings(cors_origins=(origin,)).cors_origins == (origin,)


@pytest.mark.parametrize(
    ("kwargs"),
    [{"port": 80}, {"port": 70000}, {"max_body_bytes": 10}, {"max_body_bytes": 2_000_000}, {"log_level": "TRACE"}],
)
def test_out_of_range_values_are_rejected(kwargs):
    with pytest.raises(ConfigError):
        Settings(**kwargs)


def test_environment_parsing():
    s = settings_from_environ(
        {"FINGUARD_SERVER_PORT": "9001", "FINGUARD_CORS_ORIGINS": " http://localhost:5173 , http://127.0.0.1:5173 ", "FINGUARD_LOG_LEVEL": "warning"}
    )
    assert s.port == 9001 and s.log_level == "WARNING"
    assert s.cors_origins == ("http://localhost:5173", "http://127.0.0.1:5173")


def test_environment_errors_name_the_setting_and_never_a_value():
    with pytest.raises(ConfigError) as e:
        settings_from_environ({"FINGUARD_SERVER_PORT": "abc-SECRET"})
    assert "FINGUARD_SERVER_PORT" in str(e.value) and "SECRET" not in str(e.value)
    with pytest.raises(ConfigError):
        settings_from_environ({"FINGUARD_SERVER_HOST": "0.0.0.0"})
