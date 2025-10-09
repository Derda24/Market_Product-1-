-- Create the price_history table with similar structure to products
create table if not exists public.price_history (
    id uuid default uuid_generate_v4() primary key,
    product_id uuid references public.products(id) on delete cascade,
    name text not null,
    price numeric not null,
    category text,
    store_id text,
    quantity text,
    image_url text,
    created_at timestamp with time zone default timezone('utc'::text, now()) not null
);

-- Add indexes for better performance (similar to products table)
create index if not exists idx_price_history_product_id on public.price_history(product_id);
create index if not exists idx_price_history_name on public.price_history(name);
create index if not exists idx_price_history_category on public.price_history(category);
create index if not exists idx_price_history_store_id on public.price_history(store_id);
create index if not exists idx_price_history_created_at on public.price_history(created_at);

-- Create a unique constraint to prevent duplicate price entries for the same product at the same time
create unique index if not exists idx_price_history_unique_product_time 
    on public.price_history(product_id, created_at);

-- Enable Row Level Security
alter table public.price_history enable row level security;

-- Create policies similar to products table
create policy "Allow all operations for price history"
    on public.price_history
    for all
    using (true)
    with check (true);

-- Grant access to authenticated and anon users
grant all on public.price_history to authenticated, anon;

-- Create a function to automatically insert price history when products are updated
create or replace function update_price_history()
returns trigger as $$
begin
    -- Only insert if price has changed
    if (old.price is distinct from new.price) then
        insert into public.price_history (
            product_id,
            name,
            price,
            category,
            store_id,
            quantity,
            image_url
        ) values (
            new.id,
            new.name,
            new.price,
            new.category,
            new.store_id,
            new.quantity,
            new.image_url
        );
    end if;
    return new;
end;
$$ language plpgsql;

-- Create trigger to automatically track price changes
drop trigger if exists trigger_update_price_history on public.products;
create trigger trigger_update_price_history
    after update on public.products
    for each row
    execute function update_price_history();

-- Create a function to get price history for a product
create or replace function get_product_price_history(p_product_id uuid)
returns table (
    id uuid,
    product_id uuid,
    name text,
    price numeric,
    category text,
    store_id text,
    quantity text,
    image_url text,
    created_at timestamp with time zone
) as $$
begin
    return query
    select 
        ph.id,
        ph.product_id,
        ph.name,
        ph.price,
        ph.category,
        ph.store_id,
        ph.quantity,
        ph.image_url,
        ph.created_at
    from public.price_history ph
    where ph.product_id = p_product_id
    order by ph.created_at desc;
end;
$$ language plpgsql;

-- Create a function to get price trends for a product
create or replace function get_product_price_trend(p_product_id uuid)
returns table (
    current_price numeric,
    previous_price numeric,
    price_change numeric,
    price_change_percentage numeric,
    days_since_last_change integer
) as $$
declare
    current_price_record record;
    previous_price_record record;
begin
    -- Get current price
    select price into current_price_record
    from public.products
    where id = p_product_id;
    
    -- Get previous price from price history
    select price into previous_price_record
    from public.price_history
    where product_id = p_product_id
    order by created_at desc
    limit 1;
    
    return query
    select 
        current_price_record.price as current_price,
        previous_price_record.price as previous_price,
        (current_price_record.price - previous_price_record.price) as price_change,
        case 
            when previous_price_record.price > 0 then 
                ((current_price_record.price - previous_price_record.price) / previous_price_record.price) * 100
            else 0
        end as price_change_percentage,
        extract(days from (now() - (
            select created_at 
            from public.price_history 
            where product_id = p_product_id 
            order by created_at desc 
            limit 1
        )))::integer as days_since_last_change;
end;
$$ language plpgsql;

-- Insert initial price history for existing products
insert into public.price_history (product_id, name, price, category, store_id, quantity, image_url)
select 
    id,
    name,
    price,
    category,
    store_id,
    quantity,
    image_url
from public.products
where not exists (
    select 1 from public.price_history where product_id = products.id
);

-- Create a view for easy access to current prices with price history info
create or replace view products_with_price_history as
select 
    p.id,
    p.name,
    p.price as current_price,
    p.category,
    p.store_id,
    p.quantity,
    p.image_url,
    p.created_at,
    ph.price as previous_price,
    ph.created_at as last_price_change,
    case 
        when ph.price is not null then p.price - ph.price
        else 0
    end as price_change,
    case 
        when ph.price is not null and ph.price > 0 then 
            ((p.price - ph.price) / ph.price) * 100
        else 0
    end as price_change_percentage
from public.products p
left join (
    select distinct on (product_id) 
        product_id, 
        price, 
        created_at
    from public.price_history
    order by product_id, created_at desc
) ph on p.id = ph.product_id;

-- Grant access to the view
grant select on products_with_price_history to authenticated, anon; 