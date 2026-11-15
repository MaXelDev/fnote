from fnote.model.config import Config, config_path


def test_defaults_when_missing(tmp_path):
    cfg = Config.load(tmp_path / "absent.json")
    assert cfg.vault_path == "" and 3 <= len(cfg.favorites) <= 5


def test_round_trip(tmp_path):
    path = tmp_path / "fnote" / "config.json"
    cfg = Config(vault_path="/home/x/Vault", finger_draws=True)
    cfg.save(path)
    back = Config.load(path)
    assert back.vault_path == "/home/x/Vault" and back.finger_draws is True


def test_bad_types_fall_back_to_defaults(tmp_path):
    path = tmp_path / "c.json"
    path.write_text('{"vault_path": 42, "hover_dot": false, "inconnu": 1}')
    cfg = Config.load(path)
    assert cfg.vault_path == "" and cfg.hover_dot is False


def test_corrupt_file_gives_defaults(tmp_path):
    path = tmp_path / "c.json"
    path.write_text("{pas du json")
    assert Config.load(path) == Config()


def test_xdg_config_home(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    assert config_path() == tmp_path / "fnote" / "config.json"


def test_old_plume_config_is_taken_over(monkeypatch, tmp_path):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path))
    Config(vault_path="/v").save(tmp_path / "plume" / "config.json")
    assert Config.load(config_path()).vault_path == "/v"
    assert (tmp_path / "plume" / "config.json").exists()  # l'ancien fichier n'est pas touché
