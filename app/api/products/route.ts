import { createClient } from '@supabase/supabase-js';
import { NextRequest, NextResponse } from 'next/server';

const supabase = createClient(
  process.env.SUPABASE_URL!,
  process.env.SUPABASE_SERVICE_KEY!
);

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page = parseInt(searchParams.get('page') || '1');
    const limit = parseInt(searchParams.get('limit') || '20');
    const search = searchParams.get('search') || '';
    const store = searchParams.get('store') || '';
    const city = searchParams.get('city') || '';
    const minPrice = parseFloat(searchParams.get('minPrice') || '0');
    const maxPrice = parseFloat(searchParams.get('maxPrice') || '1000');
    
    // First, get the total count
    let countQuery = supabase.from('products').select('*', { count: 'exact', head: true });
    
    // Apply filters to count query
    if (search) {
      countQuery = countQuery.ilike('name', `%${search}%`);
    }
    
    if (store) {
      countQuery = countQuery.eq('store_id', store);
    }
    // Optional city filter (only applies if 'city' column exists)
    if (city) {
      // @ts-ignore - dynamic filter if column exists
      countQuery = (countQuery as any).eq('city', city);
    }
    
    if (minPrice > 0 || maxPrice < 1000) {
      countQuery = countQuery.gte('price', minPrice).lte('price', maxPrice);
    }
    
    const { count, error: countError } = await countQuery;
    
    if (countError) {
      console.error('Count error:', countError);
      throw countError;
    }
    
    // Now get the actual data with pagination
    let dataQuery = supabase.from('products').select('*');
    
    // Apply filters to data query
    if (search) {
      dataQuery = dataQuery.ilike('name', `%${search}%`);
    }
    
    if (store) {
      dataQuery = dataQuery.eq('store_id', store);
    }
    if (city) {
      // @ts-ignore - dynamic filter if column exists
      dataQuery = (dataQuery as any).eq('city', city);
    }
    
    if (minPrice > 0 || maxPrice < 1000) {
      dataQuery = dataQuery.gte('price', minPrice).lte('price', maxPrice);
    }
    
    // Apply pagination
    const from = (page - 1) * limit;
    const to = from + limit - 1;
    dataQuery = dataQuery.range(from, to);
    
    const { data, error: dataError } = await dataQuery;
    
    if (dataError) {
      console.error('Data error:', dataError);
      throw dataError;
    }
    
    const total = count || 0;
    const totalPages = Math.ceil(total / limit);
    const hasNext = page * limit < total;
    const hasPrev = page > 1;
    
    // If city filter was applied but no products found, show all products with a message
    let fallbackMessage = null;
    let fallbackProducts = null;
    let fallbackPagination = null;
    
    if (city && total === 0) {
      // Check if there are any products at all (without city filter)
      const { count: totalCount } = await supabase
        .from('products')
        .select('*', { count: 'exact', head: true });
      
      if (totalCount && totalCount > 0) {
        fallbackMessage = `No products found for ${city}. Showing all available products instead.`;
        
        // Get all products without city filter
        let fallbackQuery = supabase.from('products').select('*');
        
        // Apply other filters (search, store, price) but not city
        if (search) {
          fallbackQuery = fallbackQuery.ilike('name', `%${search}%`);
        }
        if (store) {
          fallbackQuery = fallbackQuery.eq('store_id', store);
        }
        if (minPrice > 0 || maxPrice < 1000) {
          fallbackQuery = fallbackQuery.gte('price', minPrice).lte('price', maxPrice);
        }
        
        // Apply pagination
        const from = (page - 1) * limit;
        const to = from + limit - 1;
        fallbackQuery = fallbackQuery.range(from, to);
        
        const { data: fallbackData, error: fallbackError } = await fallbackQuery;
        
        if (!fallbackError && fallbackData) {
          fallbackProducts = fallbackData;
          const fallbackTotal = totalCount || 0;
          const fallbackTotalPages = Math.ceil(fallbackTotal / limit);
          const fallbackHasNext = page * limit < fallbackTotal;
          const fallbackHasPrev = page > 1;
          
          fallbackPagination = {
            page,
            limit,
            total: fallbackTotal,
            totalPages: fallbackTotalPages,
            hasNext: fallbackHasNext,
            hasPrev: fallbackHasPrev
          };
        }
      }
    }
    
    return NextResponse.json({ 
      products: fallbackProducts || data || [],
      pagination: fallbackPagination || {
        page,
        limit,
        total,
        totalPages,
        hasNext,
        hasPrev
      },
      fallbackMessage
    });
  } catch (error) {
    console.error('API error:', error);
    return NextResponse.json({ 
      error: 'Failed to fetch products',
      details: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}
