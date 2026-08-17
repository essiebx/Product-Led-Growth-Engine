with source as (
    select * from {{ source('raw_data', 'salesforce_deals') }}
),

renamed as (
    select
        email_hash,
        opportunity_stage,
        closed_date,
        deal_value
    from source
)

select * from renamed
