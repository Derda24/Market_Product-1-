import { OpenAI } from 'openai';
import { NextRequest, NextResponse } from 'next/server';

function buildOpenAIClient() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error('Missing OPENAI_API_KEY');
  }

  const baseURL = process.env.OPENAI_API_BASE?.trim();
  const organization = process.env.OPENAI_ORG_ID?.trim();

  return new OpenAI({
    apiKey,
    baseURL: baseURL && baseURL.length > 0 ? baseURL : undefined,
    organization: organization && organization.length > 0 ? organization : undefined,
  });
}

export async function POST(request: NextRequest) {
  let openai: OpenAI;
  try {
    openai = buildOpenAIClient();
  } catch (error) {
    return NextResponse.json(
      { reply: 'Chat assistant is not configured. Please set up your OpenAI credentials.' },
      { status: 500 }
    );
  }

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

    const model = process.env.OPENAI_MODEL || 'gpt-3.5-turbo';

    const completion = await openai.chat.completions.create({
      model,
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

      const supabaseUrl = process.env.SUPABASE_URL;
      const supabaseKey = process.env.SUPABASE_SERVICE_KEY;

      if (supabaseUrl && supabaseKey) {
        const params = new URLSearchParams();
        if (parsed.store) params.append('store_id', parsed.store.toLowerCase());
        if (parsed.category) params.append('category', parsed.category);
        if (parsed.price_max) params.append('price_max', parsed.price_max);

        const dbRes = await fetch(`${supabaseUrl}/products?${params.toString()}`, {
          headers: {
            apikey: supabaseKey
          }
        });

        if (dbRes.ok) {
          const products = await dbRes.json();

          if (Array.isArray(products) && products.length > 0) {
            reply = products
              .slice(0, 3)
              .map((p: any) => `🛒 ${p.name} — €${p.price}`)
              .join('\n');
          } else {
            reply = 'No products found. Try another query?';
          }
        } else {
          console.warn('Supabase query failed', await dbRes.text());
        }
      }
    } catch (e) {
      // Not JSON, or database fetch failed – use the AI's reply
    }

    return NextResponse.json({ reply });
  } catch (error) {
    console.error(error);
    return NextResponse.json({ reply: 'Something went wrong 😔' }, { status: 500 });
  }
}
