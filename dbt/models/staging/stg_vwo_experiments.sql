with source as (
   select * from {{ source('raw_data', 'vwo_experiments') }}
),

renamed as (
    select
        email_hash,
        experiment_id,
        variant_name
    from source
)

select * from renamed
