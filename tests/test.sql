{{
    config_block(
        materialize="table",
        target_schema="lake_test",
        strategy="append",
        type="hive"
    )
}}

with test as (
    select
        1 as number_col,
        comp_id,
        subjectid,
        street_name
    from {{ source_table("pipeline2") }}
)
select
    1 as number_col,
    comp_id,        
    subjectid,
    street_name
from test s
left join {{ ref("pipeline1") }} t on s.comp_id = t.comp_id