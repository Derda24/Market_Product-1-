import { useState } from 'react';
import ChatAssistant from './ChatAssistant';

export default function FloatingChatWidget() {
  const [open, setOpen] = useState(false);

  return (
    <>
      {/* Floating Button */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-6 right-6 z-50 bg-blue-600 text-white rounded-full shadow-lg w-14 h-14 flex items-center justify-center hover:bg-blue-700 focus:outline-none"
        aria-label="Open chat assistant"
      >
        {open ? (
          <span className="text-2xl">✖️</span>
        ) : (
          <span className="text-2xl">💬</span>
        )}
      </button>

      {/* Chat Box */}
      {open && (
        <div className="fixed bottom-24 right-6 z-50 w-80 max-w-full">
          <ChatAssistant />
        </div>
      )}
    </>
  );
} 