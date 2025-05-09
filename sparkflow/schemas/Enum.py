from enum import Enum

class SourceType(str, Enum):
    JDBC = 'jdbc'
    HIVE = 'hive'
    S3 = 's3'

class Materialization(str, Enum):
    TABLE = "table"
    VIEW = "view"

class TableMaterializationStrategies(str, Enum):
    OVERWRITE = "overwrite"
    APPEND = "append"
    MERGE = "merge"