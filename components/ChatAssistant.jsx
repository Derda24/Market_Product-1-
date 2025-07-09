import { useState } from 'react'

const BOT_AVATAR = '🤖';
const USER_AVATAR = '🧑';

export default function ChatAssistant() {
  const [messages, setMessages] = useState([
    { sender: 'bot', text: 'Hi! What are you looking for today?' }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)

  const handleSend = async () => {
    if (!input.trim()) return

    const newMessages = [...messages, { sender: 'user', text: input }]
    setMessages(newMessages)
    setInput('')
    setLoading(true)

    // Prepare conversation history for API (last 10 messages)
    const apiMessages = newMessages.slice(-10).map(msg => ({
      role: msg.sender === 'user' ? 'user' : 'assistant',
      content: msg.text
    }))

    const res = await fetch('/api/chatbot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages: apiMessages })
    })

    const data = await res.json()
    setMessages([...newMessages, { sender: 'bot', text: data.reply }])
    setLoading(false)
  }

  return (
    <div className="max-w-md mx-auto p-4 shadow rounded-xl bg-white">
      <h2 className="text-xl font-semibold mb-4">Shopping Assistant</h2>
      <div className="h-64 overflow-y-auto space-y-2 mb-2 border p-2 rounded">
        {messages.map((msg, i) => (
          <div key={i} className={`flex items-end ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}>
            {msg.sender === 'bot' && (
              <span className="mr-2 text-2xl select-none">{BOT_AVATAR}</span>
            )}
            <span className={`inline-block px-3 py-1 rounded-xl ${msg.sender === 'user' ? 'bg-blue-200' : 'bg-gray-200'}`}>
              {msg.text}
            </span>
            {msg.sender === 'user' && (
              <span className="ml-2 text-2xl select-none">{USER_AVATAR}</span>
            )}
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          className="flex-1 border rounded px-3 py-1"
          placeholder="e.g. cheap pasta in Lidl"
        />
        <button
          onClick={handleSend}
          disabled={loading}
          className="bg-blue-500 text-white px-4 py-1 rounded hover:bg-blue-600"
        >
          {loading ? '...' : 'Send'}
        </button>
      </div>
    </div>
  )
}
