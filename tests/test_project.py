def test_project_name():
    from importlib.metadata import metadata

    project = metadata("agentguard")
    assert project["Name"] == "agentguard"
