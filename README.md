# Spark Data Pipeline Documentation

## Overview

This documentation covers a comprehensive Spark-based data pipeline framework designed for efficient ETL (Extract, Transform, Load) operations. The application allows users to define SQL transformations with configuration metadata, manage dependencies between transformations, and execute them in the correct order while handling various data sources and targets.

## Key Components

### 1. Configuration System

The application uses a YAML-based configuration system to define:
- Spark configurations
- Data sources (JDBC and Hive tables)
- Application metadata

Example configuration:

```yaml
appName: test_spark_app_scr

sparkConf:
  masterUrl: "k8s://https://master_url:6443"
  config:
    spark.sql.extensions: "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions"
    spark.hadoop.fs.s3a.endpoint: "https://xxxxxxxx:9000"
    spark.hadoop.fs.s3a.access.key: "s3key"
    spark.hadoop.fs.s3a.secret.key: "s3secret"
    spark.hadoop.fs.s3a.path.style.access: "true"
    spark.hadoop.fs.s3a.connection.ssl.enabled: "false"
    spark.hadoop.fs.s3a.impl: "org.apache.hadoop.fs.s3a.S3AFileSystem"
    
    spark.jars.ivySettings: "/home/jovyan/.ivy2/ivysettings.xml"
    spark.jars.packages: "org.apache.iceberg:iceberg-spark:1.8.0,org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.8.0,org.apache.hadoop:hadoop-aws:3.3.4,org.apache.hadoop:hadoop-common:3.3.4,org.apache.spark:spark-sql_2.12:3.5.0,org.postgresql:postgresql:42.6.0,com.microsoft.sqlserver:mssql-jdbc:11.2.3.jre17"
    
    
    spark.sql.defaultCatalog: "catalog_name"
    spark.sql.catalog.lakehouse: "org.apache.iceberg.spark.SparkCatalog"
    spark.sql.catalog.lakehouse.type: "hive"
    spark.sql.catalog.lakehouse.uri: "thrift://xxxxxx:9083"
    spark.sql.iceberg.handle-timestamp-without-timezone: "true"
    
    spark.kubernetes.authenticate.driver.serviceAccountName: "spark-sa"
    spark.kubernetes.namespace: "namespace"
    spark.kubernetes.container.image: "docker-image-path"
    spark.kubernetes.authenticate.serviceAccountName: "spark-sa"
    spark.kubernetes.container.image.pullPolicy: "IfNotPresent"
    
    spark.driver.host: "xxxxxxx"
    spark.driver.memory: "4g"
    spark.executor.instances: "10"
    spark.executor.memory: "16g"
    spark.executor.cores: "10"

    
dwh_settings: &dwh_settings
  type: jdbc
  url: jdbc:postgresql://example_id:port/db_name?sslmode=disable
  username: example_username
  password: example_password
  options:
    driver: org.postgresql.Driver
  
sources:
  - <<: *dwh_settings
    name: name_reference_to_table_in_pipeline
    table: db_name.original_table_name

  - type: hive
    name: name_reference_to_table_in_pipeline
    tableName: db_name.original_table_name
```

### 2. SQL Transformation Files

Transformations are defined in SQL files with Jinja-like templating capabilities and configuration blocks.

#### Configuration Block Syntax

Each SQL file can include a configuration block that defines how the transformation should be materialized and where the results should be stored:

```sql
{{
    config_block(
        materialize="table",          -- "table" or "view"
        target_schema="target_name",  -- Name of the target schema/table, written in config file
        strategy="merge",             -- "overwrite", "append", or "merge"
        merge_keys=["id"],            -- Keys to use for merge operations
        type="hive",                  -- "hive" or "jdbc"
        branch="test_branch"          -- only applicable for hive target (iceberg)
    )
}}

-- SQL query here
```

#### Template Functions

The following templating functions are available in SQL files:

| Function | Description | Example |
|----------|-------------|---------|
| `source_table()` | References a source table defined in the config | `{{ source_table("dim_address") }}` |
| `ref()` | References another transformation | `{{ ref("stg_dim_addr") }}` |
| Custom functions | Custom functions defined in the functions directory | `{{ up("column_name") }}` |

Example SQL file:

```sql
{{
    config_block(
        materialize="table",
        target_schema="target_sample",
        strategy="merge",
        merge_keys=["id"],
        type="hive",
        branch="test_branch"
    )
}}
select
    id,
    subjectid,
    case when comp_id like 'd2d5dfcca8bfaa08db99762cfa860072' then '11' else matrixid end as matrixid,
    streetid,
    {{ up("street_name") }} as ss,
    street_name
from
    {{ ref("stg_dim_addr") }}
union all
select
    id,
    subjectid,
    matrixid,
    streetid,
    {{ up("street_name") }} as ss,
    street_name
from
    {{ ref("daha_bir_dim") }}
```

## Project Structure

```
project/
│
├── sparkflow
│   ├── schemas
│   │   ├── QuerySchema.py
│   │   ├── Enum.py
│   │   └── ConfigSchema.py
│   ├── logging_conf.py
│   ├── core
│   │   ├── SparkManager.py
│   │   ├── QueryBuilder.py
│   │   ├── ConfigParser.py
│   │   └── AppManager.py
├── pyproject.toml
├── poetry.lock
├── main.py
├── config.yml
├── README.md
└── Makefile
```

## Execution Flow

The application follows these steps during execution:

1. Parses the configuration file
2. Initializes a Spark session with the provided configurations
3. Registers all defined source tables (JDBC and Hive)
4. Reads all SQL transformation files
5. Analyzes dependencies between transformations
6. Determines the execution order using topological sorting
7. Executes each transformation in the correct order
8. Materializes results according to the defined strategy (table or view)

## Custom Functions

You can create custom functions in Python files inside the `functions/` directory. These functions will be automatically loaded and made available for use in SQL templates.

Example function:

```python
# functions/string_functions.py

def up(column_name):
    """Convert a column to uppercase"""
    return f"upper({column_name})"

def ternary(condition, value_if_true, value_if_false, value_if_null=None):
    """SQL ternary operator"""
    if value_if_null:
        return f"CASE WHEN {condition} IS NULL THEN {value_if_null} WHEN {condition} = {value_if_true} THEN {value_if_true} ELSE {value_if_false} END"
    return f"CASE WHEN {condition} = {value_if_true} THEN {value_if_true} ELSE {value_if_false} END"
```

## Materialization Strategies

The application supports the following materialization strategies:

| Strategy | Description |
|----------|-------------|
| `overwrite` | Completely replaces the target table |
| `append` | Adds new data to the target table |
| `merge` | Updates existing rows and inserts new ones based on merge keys |

## Dependencies and Execution Order

The application automatically detects dependencies between transformations using the `{{ ref() }}` function calls and builds a directed acyclic graph (DAG) to determine the correct execution order. This ensures that all dependencies are processed before dependent transformations.

## Running the Application

To run the application, use the following code:

```python
from sparkflow.core.AppManager import AppManager

app = AppManager(
    models_dir="./models",
    functions_dir="./functions",
    config_file="./config/config.yaml"
)

app.run()
```

## Error Handling

The application provides error handling for:
- Cyclic dependencies
- Missing references
- Invalid configuration
- SQL execution errors

Error messages will be logged with detailed information to help debug issues.

## Best Practices

1. **Naming Convention**: Use a consistent naming pattern for SQL files
   - `stg_` prefix for staging models
   - `int_` prefix for intermediate models
   - `fct_` prefix for fact tables
   - `dim_` prefix for dimension tables

2. **Documentation**: Add comments in SQL files to explain complex transformations

3. **Testing**: Create smaller test datasets to validate transformations before running on full data

4. **Dependencies**: Keep the dependency graph as simple as possible to improve maintainability

## Troubleshooting

### Common Issues

1. **Dependency Cycle Detected**
   - Error: "Cycle detected in pipeline dependencies"
   - Solution: Review your SQL files to identify and break circular dependencies

2. **Table Not Found**
   - Error: "Table or view not found"
   - Solution: Verify the source table name in configuration and ensure proper access permissions

3. **Memory Issues**
   - Symptom: Spark job fails with out of memory errors
   - Solution: Adjust Spark configurations for memory allocation in the config file

### Debugging Tips

1. Use the `show_execution_graph()` method to visualize the execution plan
2. Enable detailed logging by configuring the logging level
3. Check Spark UI for execution details and performance metrics

## Advanced Features

### Custom Spark Configuration

You can customize Spark configurations in the config file:

```yaml
sparkConf:
  masterUrl: "k8s://https://kube_ip:6443"
  config:
    spark.sql.param1: 4
    spark.executor.cores: 4
    spark.executor.memory: "8g"
    spark.executor.instances: 10
    spark.driver.memory: "4g"
```

### JDBC Connection Options

Additional JDBC connection options can be specified:

```yaml
sources:
  - type: "jdbc"
    name: "postgres"
    username: "data"
    password: "your_password_here"
    table: "public.my_table"
    url: "jdbc:postgresql://localhost:5432/mydb"
    options:
      driver: "org.postgresql.Driver"
      fetchsize: "10000"
      batchsize: "5000"
```

## Conclusion

This Spark data pipeline application provides a flexible and powerful framework for building ETL pipelines with SQL transformations. The templating system, dependency management, and materialization strategies make it suitable for complex data processing workflows.