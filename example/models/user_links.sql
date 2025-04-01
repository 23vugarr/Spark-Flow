{{
    config_block(
        materialize="table",
        target_schema="merged_table",
        strategy="overwrite",
        type="jdbc",
    )
}}


select
    u.id,
    u.max_enabled_links,
    u.subscription_plan,
    l.url,
    l.title,
    l.type,
    l.provider,
    l.is_active,
    now() as load_date
from
    {{ source_table("users") }} u
left join
    {{ source_table("links") }} l
on u.id = l.user_id