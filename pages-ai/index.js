import ChatAssistant from '@/components/ChatAssistant'

export default function Home() {
  return (
    <div className="min-h-screen p-8 bg-gray-50">
      <h1 className="text-3xl font-bold mb-4">Market Products</h1>
      {/* Other content here... */}
      <ChatAssistant />
    </div>
  )
}
