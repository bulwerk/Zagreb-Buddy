'use client';

import { ChatMessage } from '@/lib/types';
import { PlaceCard } from '@/components/Places/PlaceCard';
import { FollowUpButtons } from './FollowUpButtons';
import { GoogleActions } from '@/components/Integrations/GoogleActions';

interface MessageBubbleProps {
  message: ChatMessage;
  onFollowUp?: (text: string) => void;
}

function renderMessageText(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith('**') && part.endsWith('**')) {
      return (
        <strong key={i} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={i}>{part}</span>;
  });
}

export function MessageBubble({ message, onFollowUp }: MessageBubbleProps) {
  const isUser = message.role === 'user';

  return (
    <div className={`flex flex-col ${isUser ? 'items-end' : 'items-start'} gap-1 animate-in fade-in slide-in-from-bottom-2 duration-300`}>
      <div className={`flex items-start gap-3 max-w-[85%] ${isUser ? 'flex-row-reverse' : ''}`}>
        {!isUser && (
          <div className="w-8 h-8 rounded-full bg-emerald-600 flex items-center justify-center text-sm flex-shrink-0">
            🏙️
          </div>
        )}
        <div
          className={`rounded-2xl px-4 py-3 ${
            isUser
              ? 'bg-emerald-600 text-white rounded-tr-sm'
              : 'bg-slate-800 text-slate-100 rounded-tl-sm'
          }`}
        >
          <p className="text-sm leading-relaxed whitespace-pre-wrap">
            {renderMessageText(message.content)}
          </p>
        </div>
      </div>

      {message.itinerary && message.itinerary.places.length > 0 && (
        <div className="w-full max-w-[85%] pl-11 space-y-2 mt-1">
          {message.itinerary.places.map((place, i) => (
            <PlaceCard key={place.id} place={place} index={i + 1} />
          ))}
          <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-slate-400 px-1 pt-1">
            <span>⏱ {message.itinerary.total_duration_min} min total</span>
            <span>🚶 {message.itinerary.total_walking_min} min walking</span>
            {message.itinerary.weather_note && (
              <span>🌤 {message.itinerary.weather_note}</span>
            )}
          </div>
          <GoogleActions itinerary={message.itinerary} />
        </div>
      )}

      {!isUser && message.follow_ups && message.follow_ups.length > 0 && onFollowUp && (
        <div className="w-full max-w-[85%] pl-8 mt-1">
          <FollowUpButtons suggestions={message.follow_ups} onSelect={onFollowUp} />
        </div>
      )}
    </div>
  );
}
