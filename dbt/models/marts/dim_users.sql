with hubspot as (
    select * from {{ ref('stg_hubspot_leads') }}
),
vwo as (
    select * from {{ ref('stg_vwo_experiments') }}
)

select
    h.email_hash,
    h.acquisition_source,
    v.experiment_id,
    v.variant_name
from hubspot h
left join vwo v on h.email_hash = v.email_hash
