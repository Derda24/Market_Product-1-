import { useState, useRef, useEffect } from 'react'

const BOT_AVATAR = '🤖';
const USER_AVATAR = '👤';

export default function ChatAssistant() {
  const [messages, setMessages] = useState([
    { 
      sender: 'bot', 
      text: 'Hi! I\'m your shopping assistant. I can help you find the best deals, compare prices, and discover new products. What are you looking for today?',
      timestamp: new Date()
    }
  ])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [isTyping, setIsTyping] = useState(false)
  const messagesEndRef = useRef(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  const handleSend = async () => {
    if (!input.trim()) return

    const userMessage = { 
      sender: 'user', 
      text: input,
      timestamp: new Date()
    }
    const newMessages = [...messages, userMessage]
    setMessages(newMessages)
    setInput('')
    setLoading(true)
    setIsTyping(true)

    // Prepare conversation history for API (last 10 messages)
    const apiMessages = newMessages.slice(-10).map(msg => ({
      role: msg.sender === 'user' ? 'user' : 'assistant',
      content: msg.text
    }))

    try {
      const res = await fetch('/api/chatbot', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages })
      })

      const data = await res.json()
      
      // Simulate typing delay for better UX
      setTimeout(() => {
        setMessages([...newMessages, { 
          sender: 'bot', 
          text: data.reply,
          timestamp: new Date()
        }])
        setLoading(false)
        setIsTyping(false)
      }, 1000)
    } catch (error) {
      setMessages([...newMessages, { 
        sender: 'bot', 
        text: 'Sorry, I\'m having trouble connecting right now. Please try again in a moment.',
        timestamp: new Date()
      }])
      setLoading(false)
      setIsTyping(false)
    }
  }

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const formatTime = (timestamp) => {
    return timestamp.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
  }

  return (
    <div className="flex flex-col h-96">
      {/* Messages Container */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gradient-to-b from-gray-50/50 to-white/50">
        {messages.map((msg, i) => (
          <div key={i} className={`flex items-start space-x-3 ${msg.sender === 'user' ? 'flex-row-reverse space-x-reverse' : ''}`}>
            {/* Avatar */}
            <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${
              msg.sender === 'user' 
                ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white' 
                : 'bg-gradient-to-br from-gray-100 to-gray-200 text-gray-600'
            }`}>
              {msg.sender === 'user' ? USER_AVATAR : BOT_AVATAR}
            </div>

            {/* Message Bubble */}
            <div className={`flex-1 max-w-xs lg:max-w-md ${msg.sender === 'user' ? 'flex justify-end' : ''}`}>
              <div className={`relative px-4 py-2 rounded-2xl shadow-sm ${
                msg.sender === 'user'
                  ? 'bg-gradient-to-br from-blue-500 to-indigo-600 text-white'
                  : 'bg-white border border-gray-200 text-gray-800'
              }`}>
                <p className="text-sm leading-relaxed">{msg.text}</p>
                
                {/* Message timestamp */}
                <div className={`text-xs mt-1 ${
                  msg.sender === 'user' ? 'text-blue-100' : 'text-gray-500'
                }`}>
                  {formatTime(msg.timestamp)}
                </div>

                {/* Message tail */}
                <div className={`absolute top-3 w-2 h-2 transform rotate-45 ${
                  msg.sender === 'user'
                    ? 'bg-gradient-to-br from-blue-500 to-indigo-600 -right-1'
                    : 'bg-white border-r border-b border-gray-200 -left-1'
                }`}></div>
              </div>
            </div>
          </div>
        ))}

        {/* Typing indicator */}
        {isTyping && (
          <div className="flex items-start space-x-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-full bg-gradient-to-br from-gray-100 to-gray-200 flex items-center justify-center text-sm">
              {BOT_AVATAR}
            </div>
            <div className="flex-1 max-w-xs lg:max-w-md">
              <div className="bg-white border border-gray-200 rounded-2xl px-4 py-2 shadow-sm">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Container */}
      <div className="p-4 bg-gradient-to-r from-gray-50/80 to-white/80 border-t border-gray-200/50">
        <div className="flex items-end space-x-3">
          <div className="flex-1 relative">
            <textarea
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask me about products, prices, or deals..."
              className="w-full px-4 py-3 pr-12 text-sm border border-gray-300 rounded-2xl resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white/90 backdrop-blur-sm"
              rows="1"
              style={{ minHeight: '44px', maxHeight: '120px' }}
            />
            
            {/* Send button inside input */}
            <button
              onClick={handleSend}
              disabled={loading || !input.trim()}
              className={`absolute right-2 bottom-2 p-2 rounded-full transition-all duration-200 ${
                loading || !input.trim()
                  ? 'text-gray-400 cursor-not-allowed'
                  : 'text-blue-600 hover:text-blue-700 hover:bg-blue-50'
              }`}
            >
              {loading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Quick suggestions */}
        <div className="mt-3 flex flex-wrap gap-2">
          {['Find cheap pasta', 'Best deals today', 'Compare prices', 'Organic products'].map((suggestion, index) => (
            <button
              key={index}
              onClick={() => setInput(suggestion)}
              className="px-3 py-1 text-xs bg-gradient-to-r from-blue-50 to-indigo-50 text-blue-700 rounded-full border border-blue-200 hover:from-blue-100 hover:to-indigo-100 transition-all duration-200"
            >
              {suggestion}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
