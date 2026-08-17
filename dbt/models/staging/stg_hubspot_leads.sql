with source as (
    select * from {{ source('raw_data', 'hubspot_leads') }}
)

select
    email_hash,
    cta_click_date,
    coalesce(nullif(acquisition_source, ''), 'Unknown') as acquisition_source
from source