import sparkflow.core.AppManager as sparkflow

flow = sparkflow.AppManager(
    config_file="./config.yml",
    models_dir="./example/models",
    functions_dir="./example/functions",
)

flow.run()
