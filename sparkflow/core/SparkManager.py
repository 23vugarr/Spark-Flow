from pyspark.sql import SparkSession
from sparkflow.schemas.ConfigSchema import SparkConf as spark_conf_schema
from sparkflow.schemas.ConfigSchema import Source
from pyspark.conf import SparkConf
from sparkflow.schemas.Enum import TableMaterializationStrategies
from typing import List, Optional
from sparkflow.logging_conf import logger


class SparkManager:
    def __init__(self, spark_conf: spark_conf_schema, app_name: str, **kwargs):
        master_spark_conf = SparkConf()
        for key, val in spark_conf.config.items():
            master_spark_conf.set(key, str(val))

        self.spark: SparkSession = (
            SparkSession.builder.master(spark_conf.masterUrl)
            .config(conf=master_spark_conf)
            .appName(app_name)
            .enableHiveSupport()
            .getOrCreate()
        )

    def add_spark_conf(self, key: str, value: str):
        self.spark.conf.set(key, value)
        print(f"Set Spark configuration: {key} = {value}")

    def register_jdbc_table(self, source: Source):
        properties = {
            "user": str(source.username),
            "password": source.password.get_secret_value(),
        }
        if source.options:
            for key, value in source.options.items():
                properties[key] = value

        try:
            df = self.spark.read.jdbc(
                url=source.url, table=source.table, properties=properties
            )
            df.createOrReplaceTempView(source.name)
            return df
        except Exception as e:
            print(f"Error reading table {source.table} from {source.url}: {e}")
            
        return None

    def load_to_jdbc(
        self, transformation_name: str, trasform_target: Source, strategy: str
    ):
        # not done
        df_temp = self.spark.table(transformation_name)
        logger.info("Loading to jdbc table {}".format(transformation_name))

        properties = {
            "user": str(trasform_target.username),
            "password": trasform_target.password.get_secret_value(),
        }

        if trasform_target.options:
            for key, value in trasform_target.options.items():
                properties[key] = value

        df_temp.write.mode(strategy).jdbc(trasform_target.url, trasform_target.table, properties=properties)
        

    def load_to_hive(
        self,
        transformation_name: str,
        trasform_target: str,
        strategy: str,
        merge_keys: Optional[List[str]] = None,
        branch: Optional[str] = None,
    ):
        df_temp = self.spark.table(transformation_name)
        logger.info("Loading into hive table {}".format(transformation_name))

        if branch is not None:
            branch_exists = False

            branches_df = self.spark.sql(f"select * from {trasform_target}.refs")
            existing_branches = [row.name for row in branches_df.collect()]

            if f"{branch}" in existing_branches:
                branch_exists = True

            if not branch_exists:
                self.spark.sql(f"ALTER TABLE {trasform_target} CREATE BRANCH {branch}")

            trasform_target = f"{trasform_target}.branch_{branch}"

        if strategy == TableMaterializationStrategies.OVERWRITE:
            df_temp.write.format("iceberg").mode("overwrite").saveAsTable(
                trasform_target
            )
        elif strategy == TableMaterializationStrategies.APPEND:
            df_temp.write.format("iceberg").mode("append").saveAsTable(trasform_target)
        elif strategy == TableMaterializationStrategies.MERGE:
            if not merge_keys or len(merge_keys) == 0:
                raise ValueError("Merge keys must be provided for merge strategy.")

            merge_condition = " AND ".join(
                [f"t1.{key} = t2.{key}" for key in merge_keys]
            )

            self.spark.sql(
                f"""
                MERGE INTO {trasform_target} t1
                USING {transformation_name} t2
                ON {merge_condition}
                WHEN MATCHED THEN
                    UPDATE SET *
                WHEN NOT MATCHED THEN
                    INSERT *
            """
            )

        else:
            raise ValueError("Invalid strategy provided.")

    def execute_query(self, query_sql: str):
        return self.spark.sql(query_sql).show()

    def create_temp_view(self): ...

    def register_hive_table(self, source: Source):
        df = self.spark.sql(f"SELECT * FROM {source.tableName}")
        df.createOrReplaceTempView(source.name)

    def register_spark_table(self, name, query_sql):
        df = self.spark.sql(query_sql)
        df.createOrReplaceTempView(name)
