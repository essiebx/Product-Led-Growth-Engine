with hubspot as (
    select * from {{ ref('stg_hubspot_leads') }}
),
salesforce as (
    select * from {{ ref('stg_salesforce_deals') }}
),
vwo as (
    select * from {{ ref('stg_vwo_experiments') }}
)

select
    h.email_hash,
    h.cta_click_date,
    h.acquisition_source,
    v.experiment_id,
    v.variant_name,
    s.opportunity_stage,
    s.closed_date,
    s.deal_value,
    case when s.opportunity_stage = 'Closed Won' then 1 else 0 end as is_converted
from hubspot h
left join vwo v on h.email_hash = v.email_hash
left join salesforce s on h.email_hash = s.email_hash
