
import json
from config_models import UserConfiguration

print(json.dumps(UserConfiguration.schema(), indent=2))
