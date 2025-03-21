from sparkflow.schemas.ConfigSchema import ConfigModel, SparkConf, Source
from typing import Optional, List
from pydantic import ValidationError
import yaml


class ConfigParser:
    def __init__(self, config_file: Optional[str] = None):
        if not config_file:
            raise ValueError("You must provide either config_data or config_file.")

        self.config_model = None

        self.load_from_file(config_file)

    def load_from_file(self, file_path: str):
        try:
            with open(file_path, "r") as f:
                config_dict = yaml.safe_load(f)
            self.config_model = ConfigModel(**config_dict)
            print("Configuration parsed successfully.")
        except FileNotFoundError:
            print(f"Configuration file {file_path} not found.")
            raise
        except yaml.YAMLError as ye:
            print(f"Error parsing YAML file {file_path}: {ye}")
            raise
        except ValidationError as ve:
            print("Configuration validation failed:")
            print(ve.json())
            raise

    def get_config(self) -> ConfigModel:
        if not self.config_model:
            raise ValueError("Configuration has not been loaded.")
        return self.config_model

    def get_spark_conf(self) -> SparkConf:
        return self.get_config().sparkConf

    def get_sources(self) -> List[Source]:
        return self.get_config().sources

    def get_sources_by_type(self, source_type: str) -> List[Source]:
        return self.get_config().get_sources_by_type(source_type)

    def get_source_by_name(self, name: str) -> Source:
        for source in self.get_sources():
            if source.name == name:
                return source
        raise ValueError(f"Source with name '{name}' not found.")
