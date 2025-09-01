from config_models import UserConfiguration

def test_user_configuration():
    config_data = {
        "user_id": "test_user",
        "chat_provider_config": {
            "provider_name": "dummy",
            "provider_config": {}
        },
        "queue_config": {}
    }
    config = UserConfiguration(**config_data)
    assert config.user_id == "test_user"
    assert config.chat_provider_config.provider_name == "dummy"
    assert config.queue_config.max_messages == 10
