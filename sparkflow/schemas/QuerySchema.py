from pydantic import BaseModel
from typing import List, Optional

class QueryConfig(BaseModel):
    materialization: str
    pipeline_name: str
    target_schema: str
    type: str
    strategy: str
    merge_keys: List[str]
    branch: Optional[str]

class QuerySchema(BaseModel):
    file_name: str
    query_config: QueryConfig
    query: str
    dependencies: List[str]
    source_tables: Optional[List[str]]
