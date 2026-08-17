with source as (
    select * from {{ source('raw_data', 'hubspot_leads') }}
),

renamed as (
    select
        email_hash,
        cta_click_date,
        acquisition_source
    from source
)

select * from renamed
