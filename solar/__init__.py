import tomllib
import io
from pathlib import Path


__all__ = ["CONST", "COLOR", "SIM", "load_conf"]


def load_conf(fileobj: io.IOBase):
    data = tomllib.load(fileobj)
    return data


script_dir = Path(__file__).parent
config_path = script_dir / "../config.toml"
with open(config_path, "rb") as f:
    conf = load_conf(f)
    CONST = conf["constants"]
    COLOR = conf["colors"]
    SIM = conf["simulation"]
