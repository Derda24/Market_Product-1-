import { NextRequest, NextResponse } from 'next/server';
import cities from '../../../data/cities_es.json';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const q = (searchParams.get('q') || '').toLowerCase();
    const limit = parseInt(searchParams.get('limit') || '20');

    let results = cities as any[];
    if (q) {
      results = results.filter((c) =>
        c.name.toLowerCase().includes(q) || (c.region?.toLowerCase() || '').includes(q)
      );
    }

    return NextResponse.json({ cities: results.slice(0, limit) });
  } catch (error) {
    console.error('Cities API error:', error);
    return NextResponse.json({ error: 'Failed to fetch cities' }, { status: 500 });
  }
}


