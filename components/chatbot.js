import { OpenAI } from 'openai'

const openai = new OpenAI({ apiKey: process.env.OPENAI_API_KEY })

export default async function handler(req, res) {
  if (req.method !== 'POST') return res.status(405).end()

  const { message } = req.body

  try {
    const completion = await openai.chat.completions.create({
      model: 'gpt-3.5-turbo',
      messages: [
        {
          role: 'system',
          content:
            'You are an assistant that turns shopping requests into JSON filters. Output only JSON. Example input: "cheap milk in Lidl" → {"category": "milk", "store": "lidl", "price_order": "asc"}'
        },
        { role: 'user', content: message }
      ]
    })

    const parsed = JSON.parse(completion.choices[0].message.content)

    // Basic Supabase query using fetch (replace with your SDK)
    const params = new URLSearchParams()
    if (parsed.store) params.append('store_id', parsed.store.toLowerCase())
    if (parsed.category) params.append('category', parsed.category)
    if (parsed.price_max) params.append('price_max', parsed.price_max)

    const dbRes = await fetch(`${process.env.SUPABASE_URL}/products?${params.toString()}`, {
      headers: {
        apikey: process.env.SUPABASE_SERVICE_KEY
      }
    })

    const products = await dbRes.json()

    if (products.length === 0) {
      return res.json({ reply: 'No products found. Try another query?' })
    }

    const reply = products
      .slice(0, 3)
      .map((p) => `🛒 ${p.name} — €${p.price}`)
      .join('\n')

    return res.json({ reply })
  } catch (error) {
    console.error(error)
    return res.status(500).json({ reply: 'Something went wrong 😔' })
  }
}
