import json

import pywintypes

from src.config import config as config_module


def test_api_key_is_saved_encrypted_and_cleared(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "app_dir", lambda: tmp_path)
    config = config_module.Config()
    config.profile.job_title = "测试岗位"
    config.profile.hide_taskbar = False
    config.save()
    config.save_api_key("sk-test-local-only")

    assert b"sk-test-local-only" not in config.key_path.read_bytes()
    assert "sk-test-local-only" not in config.path.read_text(encoding="utf-8")
    assert config_module.Config().api_key() == "sk-test-local-only"
    assert config_module.Config().profile.hide_taskbar is False

    config.clear()
    assert not config.key_path.exists()
    assert json.loads(config.path.read_text(encoding="utf-8"))["job_title"] == ""


def test_unreadable_encrypted_key_does_not_block_startup(tmp_path, monkeypatch):
    monkeypatch.setattr(config_module, "app_dir", lambda: tmp_path)
    config = config_module.Config()
    config.key_path.write_bytes(b"encrypted-key-from-another-windows-user")

    def cannot_decrypt(*args):
        raise pywintypes.error(-2146893813, "CryptUnprotectData", "无法解密", None)

    monkeypatch.setattr(config_module.win32crypt, "CryptUnprotectData", cannot_decrypt)
    assert config.api_key() == ""
    assert config.key_path.exists()
