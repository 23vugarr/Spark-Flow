from typing import List, Dict, Union
from pydantic import BaseModel, Field, SecretStr
from sparkflow.schemas.Enum import SourceType

class SparkConf(BaseModel):
    masterUrl: str = "local"
    config: Dict[str, Union[int, float, str]] = Field(default_factory=lambda: {"spark.sql.param1": 4})

class JDBCSource(BaseModel):
    type: SourceType = Field(default=SourceType.JDBC)
    name: str = "postgres"
    username: str = "username"
    password: SecretStr = "password"
    table: str
    url: str
    options: Dict[str, str] = Field(default_factory=dict)

class HiveSource(BaseModel):
    type: SourceType = Field(default=SourceType.HIVE)
    name: str = "lake"
    tableName: str = "table_name"

Source = Union[JDBCSource, HiveSource]

class ConfigModel(BaseModel):
    appName: str = "spark flow app"
    sparkConf: SparkConf = SparkConf()
    sources: List[Source] = Field(default_factory=lambda: [
        JDBCSource(table="public.my_table", url="jdbc:postgresql://localhost:5432/mydb"),
        HiveSource()
    ])

    def get_sources_by_type(self, source_type: SourceType) -> List[Source]:
        return [source for source in self.sources if source.type == source_type]
