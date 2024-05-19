import os
import json
import dataclasses
import rich.console


@dataclasses.dataclass(slots=True)
class ConfigValues:
    groq_api_key: str = ""
    model_name: str = "llama3-70b-8192"


class ConfigManager:
    values: ConfigValues

    def __init__(self):
        self.load_config()

    @property
    def config_directory(self):
        return os.path.join(os.path.expanduser("~"), ".config", "needto")

    @property
    def config_path(self):
        return os.path.join(self.config_directory, "config.json")

    def load_config(self):
        console = rich.console.Console()
        default_config = ConfigValues()
        try:
            with open(self.config_path, "r") as fp:
                config_dict = json.load(fp)
        except (FileNotFoundError, json.JSONDecodeError):
            self.values = default_config
            self.save_config()
            console.print(
                "Config file not found or invalid. Please run `needto config` to make changes to default config."
            )
            return

        self.values = ConfigValues(
            **{k: v for k, v in config_dict.items() if hasattr(default_config, k)}
        )
        if missing_values := set(dataclasses.asdict(default_config)) - set(config_dict):
            self.save_config()
            console.print(
                f"Config file was missing {missing_values} values. "
                "It's now added automatically. "
                "Please run `needto config` to review."
            )

    def save_config(self):
        os.makedirs(os.path.dirname(self.config_path), exist_ok=True)
        with open(self.config_path, "w") as f:
            json.dump(dataclasses.asdict(self.values), f, indent=4)


config_manager = ConfigManager()
