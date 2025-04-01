from sparkflow.core.ConfigParser import ConfigParser
from sparkflow.core.SparkManager import SparkManager
from sparkflow.core.QueryBuilder import QueryBuilder
from sparkflow.schemas.QuerySchema import QuerySchema
from sparkflow.core.DataLineageVisualizer import DataLineageVisualizer
from sparkflow.schemas.Enum import SourceType, Materialization
from typing import Dict, List
import os
from collections import deque
from sparkflow.logging_conf import logger

class AppManager:
    def __init__(self, models_dir: str, functions_dir: str, config_file: str, **kwargs):
        self.parser: ConfigParser = ConfigParser(config_file=config_file)

        self.spark_manager: SparkManager = SparkManager(
            self.parser.config_model.sparkConf,
            app_name=self.parser.config_model.appName,
        )

        self.query_builder: QueryBuilder = QueryBuilder(
            models_dir=models_dir, functions_dir=functions_dir
        )

        self.source_list: dict = {}
        self.transform_queries: Dict[str, QuerySchema] = (
            {}
        )  # filename: (sql, dependencies)
        self.models_dir = models_dir
        self.execution_order: List[str] = (
            list()
        )  

        self.data_linage_visualizer = DataLineageVisualizer()

    def register_sources_as_tables(self):
        for source in self.parser.get_sources():
            if source.type == SourceType.JDBC:
                self.source_list[source.name] = self.spark_manager.register_jdbc_table(
                    source
                )
            elif source.type == SourceType.HIVE:
                self.source_list[source.name] = self.spark_manager.register_hive_table(
                    source
                )
            else:
                continue

    def register_pipelines_as_tables(self):
        for query in self.execution_order:
            print(query)
            self.spark_manager.register_spark_table(
                query, self.transform_queries[f"{query}.sql"].query
            )

    def read_sql_queries(self):
        logger.info("Reading sql files...")
        for root, _, files in os.walk(self.models_dir):
            for file in files:
                if file.lower().endswith(".sql"):
                    if "ipynb_checkpoints" in root:
                        continue
                    file_path = os.path.join(root, file)
                    relative_path = os.path.relpath(file_path, self.models_dir)
                    self.transform_queries[file] = self.query_builder.read_sql_jinja(
                        relative_path
                    )
                    logger.info(f"Read file: {file}")

    def build_execution_graph(self):
        # map pipelines to dependencies
        dependency_map = {}
        for filename, pipe in self.transform_queries.items():
            pipeline_name = filename.split(".")[0]
            dependencies = pipe.dependencies
            dependency_map[pipeline_name] = dependencies

        logger.info("Dependency map: ", dependency_map)
        self.execution_order = self._topological_sort(dependency_map)
        logger.info("Execution order: {}".format(self.execution_order))

    def _topological_sort(self, dependency_map):
        # https://www.geeksforgeeks.org/topological-sorting/
        adj = {}  # Adjacency list: {node: [children]} (reverse of dependencies)
        indegree = {}

        for pipeline in dependency_map:
            indegree[pipeline] = 0
            if pipeline not in adj:
                adj[pipeline] = []

        for node, deps in dependency_map.items():
            for dep in deps:
                if dep not in adj:
                    adj[dep] = []
                    indegree[dep] = 0
                adj[dep].append(node)
                indegree[node] += 1

        queue = deque([n for n in indegree if indegree[n] == 0])
        order = []

        while queue:
            node = queue.popleft()
            order.append(node)

            for child in adj[node]:
                indegree[child] -= 1
                if indegree[child] == 0:
                    queue.append(child)

        if len(order) != len(indegree):
            raise Exception("Cycle detected in pipeline dependencies.")

        return order

    def load_to_tables(self):
        for pipe_name in self.execution_order:
            transformation = self.transform_queries[f"{pipe_name}.sql"]
            if transformation.query_config.materialization == Materialization.TABLE:
                if transformation.query_config.type == SourceType.HIVE:
                    table = self.parser.get_source_by_name(
                        transformation.query_config.target_schema
                    )
                    self.spark_manager.load_to_hive(
                        pipe_name,
                        table.table,
                        transformation.query_config.strategy,
                        transformation.query_config.merge_keys,
                        transformation.query_config.branch,
                    )

                    print(
                        "PIPELINE DONE: ",
                        transformation.query_config.target_schema,
                        table,
                    )
                elif transformation.query_config.type == SourceType.JDBC:
                    # not done
                    table = self.parser.get_source_by_name(
                        transformation.query_config.target_schema
                    )
                    self.spark_manager.load_to_jdbc(
                        pipe_name, table, transformation.query_config.strategy
                    )

            elif transformation.query_config.materialization == Materialization.VIEW:
                self.spark_manager.execute_query(transformation.query)

    def execute_table_materialization(self, pipeline: QuerySchema):
        if pipeline.query_config.type == SourceType.JDBC:
            self.spark_manager.load_to_jdbc()

    def reload_files(self): ...

    def show_execution_graph(self):
        print(self.execution_order)

    def get_data_lineage(self):
        data_lineage = {}

        for key, val in self.transform_queries.items():
            data_lineage[key] = [
                ("references", val.dependencies),
                ("sources", val.source_tables),
            ]

        self.data_linage_visualizer.visualize(data_lineage)

    def run(self):
        self.register_sources_as_tables()
        self.read_sql_queries()
        self.build_execution_graph()
        self.register_pipelines_as_tables()
        self.load_to_tables()
        self.get_data_lineage()
