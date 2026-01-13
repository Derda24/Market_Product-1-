import { OpenAI } from 'openai';
import { NextRequest, NextResponse } from 'next/server';

function buildOpenAIClient() {
  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    throw new Error('Missing OPENAI_API_KEY environment variable');
  }

  const baseURL = process.env.OPENAI_API_BASE?.trim();
  const organization = process.env.OPENAI_ORG_ID?.trim();

  // Validate baseURL format if provided
  if (baseURL && baseURL.length > 0) {
    try {
      new URL(baseURL);
    } catch (e) {
      throw new Error(`Invalid base URL format: ${baseURL}`);
    }
  }

  const config: any = {
    apiKey,
  };

  if (baseURL && baseURL.length > 0) {
    config.baseURL = baseURL;
  }

  if (organization && organization.length > 0) {
    config.organization = organization;
  }

  return new OpenAI(config);
}

export async function POST(request: NextRequest) {
  let openai: OpenAI;
  try {
    openai = buildOpenAIClient();
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error';
    console.error('OpenAI client initialization error:', errorMessage);
    return NextResponse.json(
      { reply: `Chat assistant configuration error: ${errorMessage}` },
      { status: 500 }
    );
  }

  try {
    const body = await request.json();
    const { messages } = body;

    if (!messages || !Array.isArray(messages)) {
      return NextResponse.json(
        { reply: 'Invalid request: messages array is required.' },
        { status: 400 }
      );
    }

    // System prompt
    const systemPrompt = {
      role: 'system' as const,
      content: `You are a friendly shopping assistant for a country is chosen by the user supermarket comparison site. 
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
    console.error('Chatbot API Error:', error);
    
    // Provide more specific error messages
    let errorMessage = 'Something went wrong 😔';
    
    if (error instanceof Error) {
      // Check for common OpenAI API errors
      if (error.message.includes('API key')) {
        errorMessage = 'Invalid API key. Please check your OpenAI API configuration.';
      } else if (error.message.includes('rate limit')) {
        errorMessage = 'Rate limit exceeded. Please try again later.';
      } else if (error.message.includes('network') || error.message.includes('fetch')) {
        errorMessage = 'Network error. Please check your connection and API endpoint.';
      } else if (error.message.includes('Invalid base URL')) {
        errorMessage = 'Invalid API base URL. Please check your OPENAI_API_BASE configuration.';
      } else {
        // Log the actual error for debugging
        console.error('Detailed error:', {
          message: error.message,
          stack: error.stack,
          name: error.name
        });
        errorMessage = `Error: ${error.message}`;
      }
    }
    
    return NextResponse.json({ reply: errorMessage }, { status: 500 });
  }
}
