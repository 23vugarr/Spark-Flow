from pydantic import BaseModel
from typing import List, Optional
from .Enum import Materialization, SourceType, TableMaterializationStrategies

class QueryConfig(BaseModel):
    materialization: Materialization 
    pipeline_name: str
    target_schema: str
    type: Optional[SourceType] 
    strategy: Optional[TableMaterializationStrategies]
    merge_keys: List[str]
    branch: Optional[str]

class QuerySchema(BaseModel):
    file_name: str
    query_config: QueryConfig
    query: str
    dependencies: List[str]
    source_tables: Optional[List[str]]
