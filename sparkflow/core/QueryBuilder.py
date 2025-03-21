import os
import re
from sparkflow.schemas.QuerySchema import QueryConfig, QuerySchema
import jinja2
from sparkflow.logging_conf import logger
import importlib


class QueryBuilder:
    def __init__(self, models_dir: str, functions_dir: str = None):
        self.environment = jinja2.Environment(
            loader=jinja2.FileSystemLoader(models_dir),
            trim_blocks=True,
            lstrip_blocks=True,
        )

        if functions_dir is not None:
            for file in os.listdir(functions_dir):
                if file.endswith(".py"):
                    module_name = re.sub(r"\.py$", "", file)
                    if functions_dir.startswith("./"):
                        module_pkg = functions_dir[2:]

                    module_pkg = re.sub(r"/", ".", module_pkg)
                    
                    module = importlib.import_module(
                        f"{module_pkg}.{module_name}", package=None
                    )
                    self.environment.globals.update(
                        {
                            f"{module_name}": getattr(module, module_name),
                        }
                    )

        self.source_tables = []
        self.config_block = {}
        self.ref_tables = []

    def source_table(self, table_name: str):
        self.source_tables.append(table_name)
        return f"{table_name}"

    def config_func(self, **kwargs):
        self.config_block = dict(kwargs)
        return ""

    def ref(self, table_name: str):
        self.ref_tables.append(table_name)
        return f"{table_name}"

    def read_sql_jinja(self, file_path: str) -> QuerySchema:
        template = self.environment.get_template(file_path)
        rdr = template.render(
            source_table=self.source_table, config_block=self.config_func, ref=self.ref
        )

        qconfig = QueryConfig(
            materialization=self.config_block.get("materialize", "view"),
            target_schema=self.config_block.get("target_schema", ""),
            pipeline_name=os.path.basename(file_path),
            strategy=self.config_block.get("strategy", ""),
            type=self.config_block.get("type", ""),
            merge_keys=self.config_block.get("merge_keys", []),
            branch=self.config_block.get("branch", None),
        )

        qschema = QuerySchema(
            file_name=os.path.basename(file_path),
            query_config=qconfig,
            query=rdr,
            dependencies=self.ref_tables,
            source_tables=self.source_tables,
        )

        logger.info(f"Query Schema: {qschema}")
        logger.info(f"Query: {qschema.query}")

        self.config_block = {}
        self.source_tables.clear()
        self.ref_tables.clear()

        return qschema
