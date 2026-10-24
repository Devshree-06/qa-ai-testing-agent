import os
from collections.abc import Mapping


_BASE_ENVIRONMENT_KEYS = {
    "comspec",
    "home",
    "homedrive",
    "homepath",
    "path",
    "pathext",
    "systemdrive",
    "systemroot",
    "temp",
    "tmp",
    "windir",
    "tmpdir",
}
_ALLOWLIST_VARIABLE = "QA_AGENT_TEST_ENV_ALLOWLIST"
_SENSITIVE_NAME_MARKERS = {
    "auth",
    "credential",
    "password",
    "private",
    "secret",
    "token",
}


def _is_sensitive_name(name: str) -> bool:
    normalized_name = name.casefold()
    return any(marker in normalized_name for marker in _SENSITIVE_NAME_MARKERS) or (
        normalized_name.endswith("_key") or normalized_name == "key"
    )


def build_test_environment(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Build a minimal child environment without inheriting agent secrets."""
    source = os.environ if source is None else source
    values_by_name = {name.casefold(): (name, value) for name, value in source.items()}
    allowed_names = set(_BASE_ENVIRONMENT_KEYS)

    configured_names = values_by_name.get(_ALLOWLIST_VARIABLE.casefold(), ("", ""))[1]
    allowed_names.update(
        name.strip().casefold()
        for name in configured_names.split(",")
        if name.strip()
    )

    return {
        original_name: value
        for name, (original_name, value) in values_by_name.items()
        if name in allowed_names and not _is_sensitive_name(name)
    }