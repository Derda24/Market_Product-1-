-- Migration: Create secure RLS policies for team access control
-- Date: 2024-07-05
-- Description: Implements comprehensive security policies to prevent unauthorized changes

-- Enable RLS on existing tables
ALTER TABLE public.products ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.price_history ENABLE ROW LEVEL SECURITY;

-- ============================================================================
-- PRODUCTS TABLE POLICIES
-- ============================================================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow public read access to products" ON public.products;
DROP POLICY IF EXISTS "Allow authenticated users to insert products" ON public.products;
DROP POLICY IF EXISTS "Allow authenticated users to update products" ON public.products;
DROP POLICY IF EXISTS "Allow authenticated users to delete products" ON public.products;

-- 1. PUBLIC READ ACCESS - Anyone can read products (for your app)
CREATE POLICY "Allow public read access to products" ON public.products
    FOR SELECT USING (true);

-- 2. INSERT POLICY - Only service role can insert (for scrapers)
CREATE POLICY "Allow service role to insert products" ON public.products
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role' OR 
        auth.jwt() ->> 'role' = 'service_role'
    );

-- 3. UPDATE POLICY - Only service role can update prices
CREATE POLICY "Allow service role to update products" ON public.products
    FOR UPDATE USING (
        auth.role() = 'service_role' OR 
        auth.jwt() ->> 'role' = 'service_role'
    );

-- 4. DELETE POLICY - Only service role can delete (prevent accidental deletions)
CREATE POLICY "Allow service role to delete products" ON public.products
    FOR DELETE USING (
        auth.role() = 'service_role' OR 
        auth.jwt() ->> 'role' = 'service_role'
    );

-- ============================================================================
-- PRICE_HISTORY TABLE POLICIES
-- ============================================================================

-- Drop existing policies if they exist
DROP POLICY IF EXISTS "Allow public read access to price history" ON public.price_history;
DROP POLICY IF EXISTS "Allow authenticated users to insert price history" ON public.price_history;
DROP POLICY IF EXISTS "Allow authenticated users to update price history" ON public.price_history;
DROP POLICY IF EXISTS "Allow authenticated users to delete price history" ON public.price_history;

-- 1. PUBLIC READ ACCESS - Anyone can read price history
CREATE POLICY "Allow public read access to price history" ON public.price_history
    FOR SELECT USING (true);

-- 2. INSERT POLICY - Only service role can insert price history
CREATE POLICY "Allow service role to insert price history" ON public.price_history
    FOR INSERT WITH CHECK (
        auth.role() = 'service_role' OR 
        auth.jwt() ->> 'role' = 'service_role'
    );

-- 3. UPDATE POLICY - Only service role can update price history
CREATE POLICY "Allow service role to update price history" ON public.price_history
    FOR UPDATE USING (
        auth.role() = 'service_role' OR 
        auth.jwt() ->> 'role' = 'service_role'
    );

-- 4. DELETE POLICY - Only service role can delete price history
CREATE POLICY "Allow service role to delete price history" ON public.price_history
    FOR DELETE USING (
        auth.role() = 'service_role' OR 
        auth.jwt() ->> 'role' = 'service_role'
    );

-- ============================================================================
-- ADDITIONAL SECURITY MEASURES
-- ============================================================================

-- Create a function to log all changes (audit trail)
CREATE OR REPLACE FUNCTION log_table_changes()
RETURNS TRIGGER AS $$
BEGIN
    INSERT INTO public.price_history (
        product_id,
        old_price,
        new_price,
        changed_at
    ) VALUES (
        NEW.id,
        OLD.price,
        NEW.price,
        NOW()
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Create trigger to automatically log price changes
DROP TRIGGER IF EXISTS log_price_changes ON public.products;
CREATE TRIGGER log_price_changes
    AFTER UPDATE OF price ON public.products
    FOR EACH ROW
    WHEN (OLD.price IS DISTINCT FROM NEW.price)
    EXECUTE FUNCTION log_table_changes();

-- ============================================================================
-- TEAM ACCESS CONTROL
-- ============================================================================

-- Create a view for team members to see data without modification rights
CREATE OR REPLACE VIEW public.products_view AS
SELECT 
    id,
    name,
    price,
    category,
    store_id,
    quantity,
    created_at
FROM public.products;

-- Grant read access to the view for authenticated users
GRANT SELECT ON public.products_view TO authenticated;

-- Create a function to get price history for team analysis
CREATE OR REPLACE FUNCTION get_product_price_history(product_id UUID)
RETURNS TABLE (
    product_name TEXT,
    old_price DECIMAL,
    new_price DECIMAL,
    price_change DECIMAL,
    changed_at TIMESTAMP
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        p.name as product_name,
        ph.old_price,
        ph.new_price,
        (ph.new_price - ph.old_price) as price_change,
        ph.changed_at
    FROM public.price_history ph
    JOIN public.products p ON ph.product_id = p.id
    WHERE ph.product_id = $1
    ORDER BY ph.changed_at DESC;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Grant execute permission on the function
GRANT EXECUTE ON FUNCTION get_product_price_history(UUID) TO authenticated;

-- ============================================================================
-- COMMENTS FOR DOCUMENTATION
-- ============================================================================

COMMENT ON TABLE public.products IS 'Product catalog with RLS enabled - only service role can modify';
COMMENT ON TABLE public.price_history IS 'Price change audit trail with RLS enabled';
COMMENT ON VIEW public.products_view IS 'Read-only view for team members to access product data';
COMMENT ON FUNCTION get_product_price_history(UUID) IS 'Function for team to analyze price history';

-- ============================================================================
-- VERIFICATION QUERIES (run these to test the policies)
-- ============================================================================

-- Check if RLS is enabled on all tables
SELECT 
    schemaname,
    tablename,
    rowsecurity
FROM pg_tables 
WHERE schemaname = 'public' 
    AND tablename IN ('products', 'price_history');

-- Check existing policies
SELECT 
    schemaname,
    tablename,
    policyname,
    permissive,
    roles,
    cmd,
    qual,
    with_check
FROM pg_policies 
WHERE schemaname = 'public'
ORDER BY tablename, policyname; 