from frameworks.process_environment import build_test_environment


def test_environment_includes_runtime_and_explicitly_allowed_values():
    source = {
        "PATH": "C:/tools",
        "SYSTEMROOT": "C:/Windows",
        "QA_AGENT_TEST_ENV_ALLOWLIST": "API_BASE_URL, FEATURE_FLAG",
        "API_BASE_URL": "https://uat.example.test",
        "FEATURE_FLAG": "enabled",
        "GROQ_API_KEY": "must-not-be-forwarded",
    }

    result = build_test_environment(source)

    assert result == {
        "PATH": "C:/tools",
        "SYSTEMROOT": "C:/Windows",
        "API_BASE_URL": "https://uat.example.test",
        "FEATURE_FLAG": "enabled",
    }


def test_environment_allowlist_is_case_insensitive_and_ignores_missing_values():
    source = {
        "PATH": "C:/tools",
        "qa_agent_test_env_allowlist": "feature_flag, MISSING",
        "Feature_Flag": "enabled",
        "SECRET_TOKEN": "must-not-be-forwarded",
    }

    result = build_test_environment(source)

    assert result == {"PATH": "C:/tools", "Feature_Flag": "enabled"}


def test_environment_never_forwards_credentials_even_if_allowlisted():
    source = {
        "PATH": "C:/tools",
        "QA_AGENT_TEST_ENV_ALLOWLIST": "GROQ_API_KEY, SERVICE_TOKEN, USERNAME",
        "GROQ_API_KEY": "must-not-be-forwarded",
        "SERVICE_TOKEN": "must-not-be-forwarded",
        "USERNAME": "qa-runner",
    }

    result = build_test_environment(source)

    assert result == {"PATH": "C:/tools", "USERNAME": "qa-runner"}