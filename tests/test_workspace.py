import yaml

from researchinfra.workspace import WORKSPACE_DIRECTORIES, init_workspace


def test_init_workspace_creates_expected_structure(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "research"

    result = init_workspace(workspace)

    assert result.path == workspace.resolve()
    assert result.config.name == "research"
    for directory in WORKSPACE_DIRECTORIES:
        assert (workspace / directory).is_dir()

    config = yaml.safe_load((workspace / ".researchinfra" / "workspace.yaml").read_text())
    assert config["name"] == "research"
    assert "model_providers" in config
    assert "agent_backends" in config
    assert any(backend["backend"] == "manual" for backend in config["agent_backends"])


def test_init_workspace_with_custom_name(tmp_path) -> None:  # type: ignore[no-untyped-def]
    workspace = tmp_path / "research"

    result = init_workspace(workspace, name="Lab Workspace")

    assert result.config.name == "Lab Workspace"
    assert "Lab Workspace" in (workspace / "README.md").read_text()
