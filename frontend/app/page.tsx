'use client';

import { useState, useEffect } from 'react';
import dynamic from 'next/dynamic';
import Image from 'next/image';
import { ChatMessage, Itinerary } from '@/lib/types';
import { sendMessage } from '@/lib/api';
import { ChatWindow } from '@/components/Chat/ChatWindow';
import { ChatInput } from '@/components/Chat/ChatInput';
import { MoodSelector } from '@/components/Chat/MoodSelector';
import { Map, X, RotateCcw } from 'lucide-react';

const ZagrebMap = dynamic(
  () => import('@/components/Map/ZagrebMap').then((mod) => mod.ZagrebMap),
  { ssr: false }
);

export default function Home() {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [conversationId, setConversationId] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [activeItinerary, setActiveItinerary] = useState<Itinerary | null>(null);
  const [showMap, setShowMap] = useState(true);

  useEffect(() => {
    handleNewChat();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const welcomeMessage: ChatMessage = {
    id: 'welcome',
    role: 'assistant',
    content:
      "Bok! 👋 I'm your Zagreb Buddy — think of me as a local friend who knows all the best hidden spots. What are you in the mood for today?",
    follow_ups: [
      'I have 2 hours to explore',
      'Show me hidden gems near the center',
      "What's happening today?",
    ],
    timestamp: new Date(),
  };

  const handleNewChat = () => {
    setMessages([{ ...welcomeMessage, id: `welcome-${Date.now()}` }]);
    setConversationId(null);
    setActiveItinerary(null);
    setShowMap(true);
  };

  const handleSend = async (text: string) => {
    const userMsg: ChatMessage = {
      id: Date.now().toString(),
      role: 'user',
      content: text,
      timestamp: new Date(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsLoading(true);

    try {
      const response = await sendMessage(text, conversationId || undefined);

      setConversationId(response.conversation_id);

      const botMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message,
        itinerary: response.itinerary,
        follow_ups: response.follow_ups,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, botMsg]);

      if (response.itinerary) {
        setActiveItinerary(response.itinerary);
        setShowMap(true);
      }
    } catch {
      const errorMsg: ChatMessage = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content:
          "Joj, sorry! I'm having a bit of trouble right now. Give me a moment and try again! 🙏",
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMsg]);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-[100dvh] flex flex-col bg-slate-950 text-white">
      <header className="flex-shrink-0 px-4 py-3 border-b border-slate-800 flex items-center gap-3 bg-slate-900/95 backdrop-blur-sm">
        <Image
          src="/logo-preview.png"
          alt="Zagreb Buddy logo"
          width={26}
          height={26}
          className="rounded-md border border-slate-700 bg-white p-0.5"
          priority
        />
        <div className="flex-1">
          <h1 className="font-bold text-lg leading-tight">Zagreb Buddy</h1>
          <p className="text-xs text-slate-400">Your AI local friend</p>
        </div>
        <div className="flex items-center gap-2">
          {activeItinerary && (
            <button
              onClick={() => setShowMap(!showMap)}
              className="w-9 h-9 rounded-full bg-slate-800 hover:bg-slate-700 flex items-center justify-center transition-colors"
              aria-label={showMap ? 'Hide map' : 'Show map'}
            >
              {showMap ? <X size={16} className="text-slate-400" /> : <Map size={16} className="text-emerald-400" />}
            </button>
          )}
          {messages.length > 1 && (
            <button
              onClick={handleNewChat}
              className="w-9 h-9 rounded-full bg-slate-800 hover:bg-slate-700 flex items-center justify-center transition-colors"
              aria-label="New chat"
            >
              <RotateCcw size={16} className="text-slate-400" />
            </button>
          )}
        </div>
      </header>

      <ChatWindow messages={messages} isLoading={isLoading} onFollowUp={handleSend} />

      {activeItinerary && showMap && (
        <div className="flex-shrink-0 h-48 border-t border-slate-800 relative">
          <ZagrebMap itinerary={activeItinerary} />
        </div>
      )}

      {messages.length <= 1 && <MoodSelector onSelect={handleSend} />}

      <ChatInput onSend={handleSend} disabled={isLoading} />
    </div>
  );
}
