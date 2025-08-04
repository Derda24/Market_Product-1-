import { useState, useEffect } from 'react';
import ChatAssistant from './ChatAssistant';

export default function FloatingChatWidget() {
  const [open, setOpen] = useState(false);
  const [isVisible, setIsVisible] = useState(false);

  // Add entrance animation
  useEffect(() => {
    const timer = setTimeout(() => setIsVisible(true), 1000);
    return () => clearTimeout(timer);
  }, []);

  return (
    <>
      {/* Enhanced Floating Button with Glass Morphism */}
      <div className={`fixed bottom-6 right-6 z-50 transition-all duration-500 ease-out ${
        isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-10'
      }`}>
        <button
          onClick={() => setOpen((o) => !o)}
          className={`
            relative w-16 h-16 rounded-full shadow-2xl 
            bg-gradient-to-br from-blue-500 via-indigo-500 to-purple-600
            hover:from-blue-600 hover:via-indigo-600 hover:to-purple-700
            transform transition-all duration-300 ease-out
            hover:scale-110 hover:shadow-3xl
            focus:outline-none focus:ring-4 focus:ring-blue-300/50
            ${open ? 'rotate-45 scale-110' : 'rotate-0 scale-100'}
            backdrop-blur-sm border border-white/20
          `}
          aria-label="Open chat assistant"
        >
          {/* Animated background glow */}
          <div className="absolute inset-0 rounded-full bg-gradient-to-br from-blue-400 to-purple-500 opacity-20 animate-pulse"></div>
          
          {/* Icon with smooth transition */}
          <div className="relative z-10 flex items-center justify-center w-full h-full">
            {open ? (
              <svg className="w-6 h-6 text-white transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            ) : (
              <svg className="w-6 h-6 text-white transition-transform duration-300" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z" />
              </svg>
            )}
          </div>

          {/* Notification dot */}
          {!open && (
            <div className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-bounce">
              <div className="w-full h-full bg-red-400 rounded-full animate-ping"></div>
            </div>
          )}
        </button>
      </div>

      {/* Enhanced Chat Box with Glass Morphism */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-96 max-w-full animate-in slide-in-from-bottom-4 duration-300">
          <div className="relative">
            {/* Chat box with glass morphism effect */}
            <div className="
              bg-white/90 backdrop-blur-xl rounded-2xl shadow-2xl 
              border border-white/20 overflow-hidden
              transform transition-all duration-300 ease-out
              hover:shadow-3xl hover:scale-[1.02]
            ">
              {/* Gradient header */}
              <div className="bg-gradient-to-r from-blue-500 via-indigo-500 to-purple-600 p-4">
                <div className="flex items-center justify-between">
                  <div className="flex items-center space-x-3">
                    <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                      <span className="text-xl">🤖</span>
                    </div>
                    <div>
                      <h3 className="text-white font-semibold text-lg">Shopping Assistant</h3>
                      <p className="text-blue-100 text-sm">Ask me anything about products!</p>
                    </div>
                  </div>
                  <div className="flex items-center space-x-2">
                    <div className="w-2 h-2 bg-green-400 rounded-full animate-pulse"></div>
                    <span className="text-blue-100 text-xs">Online</span>
                  </div>
                </div>
              </div>

              {/* Chat content */}
              <ChatAssistant />
            </div>

            {/* Decorative elements */}
            <div className="absolute -top-2 -left-2 w-4 h-4 bg-gradient-to-br from-blue-400 to-purple-500 rounded-full opacity-60"></div>
            <div className="absolute -bottom-2 -right-2 w-6 h-6 bg-gradient-to-br from-indigo-400 to-purple-500 rounded-full opacity-40"></div>
          </div>
        </div>
      )}

      {/* Background overlay for focus */}
      {open && (
        <div 
          className="fixed inset-0 z-40 bg-black/20 backdrop-blur-sm"
          onClick={() => setOpen(false)}
        />
      )}
    </>
  );
} 