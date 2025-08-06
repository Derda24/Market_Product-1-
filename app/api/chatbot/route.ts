import { OpenAI } from 'openai';
import { NextRequest, NextResponse } from 'next/server';

export async function POST(request: NextRequest) {
  // Check if OpenAI API key is configured
  if (!process.env.OPENAI_API_KEY) {
    return NextResponse.json({ 
      reply: 'Chat assistant is not configured. Please set up OpenAI API key.' 
    }, { status: 500 });
  }

  const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY });

  try {
    const { messages } = await request.json();

    // System prompt
    const systemPrompt = {
      role: 'system' as const,
      content: `You are a friendly shopping assistant for a Barcelona supermarket comparison site. 
You can answer general shopping questions, chat naturally, and provide product suggestions. 
If the user asks for a product or filter, output only JSON (e.g., {"category": "milk", "store": "lidl", "price_order": "asc"}). 
For all other questions, reply conversationally.`
    };

    // Compose full message history
    const fullMessages = [systemPrompt, ...(messages || [])];

    const completion = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: fullMessages
    });

    const aiReply = completion.choices[0].message.content;
    let reply = aiReply || 'Sorry, I couldn\'t generate a response.';
    
    // Try to parse JSON if present
    try {
      if (!aiReply) {
        throw new Error('No response from AI');
      }
      const parsed = JSON.parse(aiReply);
      // Basic Supabase query using fetch (replace with your SDK)
      const params = new URLSearchParams();
      if (parsed.store) params.append('store_id', parsed.store.toLowerCase());
      if (parsed.category) params.append('category', parsed.category);
      if (parsed.price_max) params.append('price_max', parsed.price_max);

      const dbRes = await fetch(`${process.env.SUPABASE_URL}/products?${params.toString()}`, {
        headers: {
          apikey: process.env.SUPABASE_SERVICE_KEY!
        }
      });

      const products = await dbRes.json();

      if (products.length === 0) {
        reply = 'No products found. Try another query?';
      } else {
        reply = products
          .slice(0, 3)
          .map((p: any) => `🛒 ${p.name} — €${p.price}`)
          .join('\n');
      }
    } catch (e) {
      // Not JSON, just use the AI's reply
    }

    return NextResponse.json({ reply });
  } catch (error) {
    console.error(error);
    return NextResponse.json({ reply: 'Something went wrong 😔' }, { status: 500 });
  }
}
