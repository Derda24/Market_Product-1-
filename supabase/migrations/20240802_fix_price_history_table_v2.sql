-- Fix price_history table to match products table structure
-- This migration safely adds missing columns without dropping existing data

-- First, let's check what columns exist and add missing ones
DO $$
BEGIN
    -- Add name column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'price_history' 
        AND column_name = 'name'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.price_history ADD COLUMN name text;
    END IF;

    -- Add category column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'price_history' 
        AND column_name = 'category'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.price_history ADD COLUMN category text;
    END IF;

    -- Add store_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'price_history' 
        AND column_name = 'store_id'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.price_history ADD COLUMN store_id text;
    END IF;

    -- Add quantity column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'price_history' 
        AND column_name = 'quantity'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.price_history ADD COLUMN quantity text;
    END IF;

    -- Add image_url column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'price_history' 
        AND column_name = 'image_url'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.price_history ADD COLUMN image_url text;
    END IF;

    -- Add product_id column if it doesn't exist
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'price_history' 
        AND column_name = 'product_id'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.price_history ADD COLUMN product_id uuid;
    END IF;

    -- Add created_at column if it doesn't exist (matching products table structure)
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'price_history' 
        AND column_name = 'created_at'
        AND table_schema = 'public'
    ) THEN
        ALTER TABLE public.price_history ADD COLUMN created_at timestamp without time zone DEFAULT now();
    END IF;

END $$;

-- Add indexes for better performance (only if they don't exist)
CREATE INDEX IF NOT EXISTS idx_price_history_product_id ON public.price_history(product_id);
CREATE INDEX IF NOT EXISTS idx_price_history_name ON public.price_history(name);
CREATE INDEX IF NOT EXISTS idx_price_history_category ON public.price_history(category);
CREATE INDEX IF NOT EXISTS idx_price_history_store_id ON public.price_history(store_id);
CREATE INDEX IF NOT EXISTS idx_price_history_created_at ON public.price_history(created_at);

-- Create a unique constraint to prevent duplicate price entries for the same product at the same time
CREATE UNIQUE INDEX IF NOT EXISTS idx_price_history_unique_product_time 
    ON public.price_history(product_id, created_at);

-- Enable Row Level Security if not already enabled
ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;

-- Create policies similar to products table (drop existing if any)
DROP POLICY IF EXISTS "Allow all operations for price history" ON public.price_history;
CREATE POLICY "Allow all operations for price history"
    ON public.price_history
    FOR ALL
    USING (true)
    WITH CHECK (true);

-- Grant access to authenticated and anon users
GRANT ALL ON public.price_history TO authenticated, anon;

-- Drop existing functions first to avoid return type conflicts
DROP FUNCTION IF EXISTS update_price_history() CASCADE;
DROP FUNCTION IF EXISTS get_product_price_history(uuid) CASCADE;
DROP FUNCTION IF EXISTS get_product_price_trend(uuid) CASCADE;

-- Create a function to automatically insert price history when products are updated
CREATE OR REPLACE FUNCTION update_price_history()
RETURNS trigger AS $$
BEGIN
    -- Only insert if price has changed
    IF (old.price IS DISTINCT FROM new.price) THEN
        INSERT INTO public.price_history (
            product_id,
            name,
            price,
            category,
            store_id,
            quantity,
            image_url,
            created_at
        ) VALUES (
            new.id,
            new.name,
            new.price,
            new.category,
            new.store_id,
            new.quantity,
            new.image_url,
            now()
        );
    END IF;
    RETURN new;
END;
$$ LANGUAGE plpgsql;

-- Create a function to get price history for a product
CREATE OR REPLACE FUNCTION get_product_price_history(p_product_id uuid)
RETURNS TABLE (
    id uuid,
    product_id uuid,
    name text,
    price numeric,
    category text,
    store_id text,
    quantity text,
    image_url text,
    created_at timestamp without time zone
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        ph.id,
        ph.product_id,
        ph.name,
        ph.price,
        ph.category,
        ph.store_id,
        ph.quantity,
        ph.image_url,
        ph.created_at
    FROM public.price_history ph
    WHERE ph.product_id = p_product_id
    ORDER BY ph.created_at DESC;
END;
$$ LANGUAGE plpgsql;

-- Create a function to get price trends for a product
CREATE OR REPLACE FUNCTION get_product_price_trend(p_product_id uuid)
RETURNS TABLE (
    current_price numeric,
    previous_price numeric,
    price_change numeric,
    price_change_percentage numeric,
    days_since_last_change integer
) AS $$
DECLARE
    current_price_record record;
    previous_price_record record;
BEGIN
    -- Get current price
    SELECT price INTO current_price_record
    FROM public.products
    WHERE id = p_product_id;
    
    -- Get previous price from price history
    SELECT price INTO previous_price_record
    FROM public.price_history
    WHERE product_id = p_product_id
    ORDER BY created_at DESC
    LIMIT 1;
    
    RETURN QUERY
    SELECT 
        current_price_record.price AS current_price,
        previous_price_record.price AS previous_price,
        (current_price_record.price - previous_price_record.price) AS price_change,
        CASE 
            WHEN previous_price_record.price > 0 THEN 
                ((current_price_record.price - previous_price_record.price) / previous_price_record.price) * 100
            ELSE 0
        END AS price_change_percentage,
        EXTRACT(days FROM (now() - (
            SELECT created_at 
            FROM public.price_history 
            WHERE product_id = p_product_id 
            ORDER BY created_at DESC 
            LIMIT 1
        )))::integer AS days_since_last_change;
END;
$$ LANGUAGE plpgsql;

-- Update existing price history records with product information
UPDATE public.price_history 
SET 
    name = p.name,
    category = p.category,
    store_id = p.store_id,
    quantity = p.quantity,
    image_url = p.image_url
FROM public.products p
WHERE price_history.product_id = p.id
AND price_history.name IS NULL;

-- Insert initial price history for existing products that don't have history
INSERT INTO public.price_history (product_id, name, price, category, store_id, quantity, image_url, created_at)
SELECT 
    id,
    name,
    price,
    category,
    store_id,
    quantity,
    image_url,
    created_at
FROM public.products
WHERE NOT EXISTS (
    SELECT 1 FROM public.price_history WHERE product_id = products.id
);

-- Drop existing view if it exists
DROP VIEW IF EXISTS products_with_price_history;

-- Create a view for easy access to current prices with price history info
CREATE OR REPLACE VIEW products_with_price_history AS
SELECT 
    p.id,
    p.name,
    p.price AS current_price,
    p.category,
    p.store_id,
    p.quantity,
    p.image_url,
    p.created_at,
    ph.price AS previous_price,
    ph.created_at AS last_price_change,
    CASE 
        WHEN ph.price IS NOT NULL THEN p.price - ph.price
        ELSE 0
    END AS price_change,
    CASE 
        WHEN ph.price IS NOT NULL AND ph.price > 0 THEN 
            ((p.price - ph.price) / ph.price) * 100
        ELSE 0
    END AS price_change_percentage
FROM public.products p
LEFT JOIN (
    SELECT DISTINCT ON (product_id) 
        product_id, 
        price, 
        created_at
    FROM public.price_history
    ORDER BY product_id, created_at DESC
) ph ON p.id = ph.product_id;

-- Grant access to the view
GRANT SELECT ON products_with_price_history TO authenticated, anon; 