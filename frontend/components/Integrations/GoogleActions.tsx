'use client';

import { useEffect, useState } from 'react';
import { CalendarPlus, Link as LinkIcon } from 'lucide-react';
import {
  buildGoogleRoute,
  createGoogleCalendarEvent,
  getGoogleStatus,
  getGoogleConnectUrl,
} from '@/lib/api';
import { Itinerary } from '@/lib/types';

interface GoogleActionsProps {
  itinerary: Itinerary;
}

export function GoogleActions({ itinerary }: GoogleActionsProps) {
  const [isConnecting, setIsConnecting] = useState(false);
  const [isBuildingRoute, setIsBuildingRoute] = useState(false);
  const [isCreatingEvent, setIsCreatingEvent] = useState(false);
  const [isCheckingStatus, setIsCheckingStatus] = useState(true);
  const [isConnected, setIsConnected] = useState(false);

  useEffect(() => {
    const loadStatus = async () => {
      setIsCheckingStatus(true);
      try {
        const status = await getGoogleStatus();
        setIsConnected(status.connected);
      } catch (err) {
        console.error(err);
        setIsConnected(false);
      } finally {
        setIsCheckingStatus(false);
      }
    };

    void loadStatus();
  }, []);

  const onConnectGoogle = async () => {
    setIsConnecting(true);
    try {
      const result = await getGoogleConnectUrl();
      window.location.href = result.authorize_url;
    } catch (err) {
      console.error(err);
      alert('Failed to start Google connect flow.');
    } finally {
      setIsConnecting(false);
    }
  };

  const onOpenRoute = async () => {
    setIsBuildingRoute(true);
    try {
      const result = await buildGoogleRoute(itinerary.places);
      window.open(result.maps_directions_url, '_blank', 'noopener,noreferrer');
    } catch (err) {
      console.error(err);
      alert('Failed to build Google Maps route.');
    } finally {
      setIsBuildingRoute(false);
    }
  };

  const onAddCalendar = async () => {
    setIsCreatingEvent(true);
    try {
      const now = new Date();
      const start = new Date(now.getTime() + 15 * 60 * 1000);
      const end = new Date(start.getTime() + itinerary.total_duration_min * 60 * 1000);
      const names = itinerary.places.map((p) => p.name).join(' → ');

      const event = await createGoogleCalendarEvent({
        title: 'Zagreb Buddy Plan',
        description: `Suggested route: ${names}`,
        start_iso: start.toISOString(),
        end_iso: end.toISOString(),
        timezone_name: 'Europe/Zagreb',
        location: itinerary.places[0]?.name,
      });

      if (event.html_link) {
        window.open(event.html_link, '_blank', 'noopener,noreferrer');
      } else {
        alert('Calendar event created.');
      }
    } catch (err) {
      console.error(err);
      alert('Failed to create Google Calendar event. Make sure your Google account is connected.');
    } finally {
      setIsCreatingEvent(false);
    }
  };

  return (
    <div className="flex flex-wrap gap-2 pt-2">
      {isCheckingStatus ? (
        <span className="text-xs px-3 py-1.5 rounded-full border border-slate-600 text-slate-300">
          Checking Google status…
        </span>
      ) : isConnected ? (
        <span className="text-xs px-3 py-1.5 rounded-full border border-emerald-500/40 text-emerald-300 bg-emerald-500/10">
          Google connected
        </span>
      ) : (
        <button
          onClick={onConnectGoogle}
          disabled={isConnecting}
          className="text-xs px-3 py-1.5 rounded-full border border-blue-500/40 text-blue-300 hover:bg-blue-500/10 transition-colors disabled:opacity-60"
        >
          {isConnecting ? 'Connecting…' : 'Connect Google'}
        </button>
      )}

      <button
        onClick={onOpenRoute}
        disabled={isBuildingRoute || itinerary.places.length < 2}
        className="text-xs px-3 py-1.5 rounded-full border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10 transition-colors disabled:opacity-60 inline-flex items-center gap-1"
      >
        <LinkIcon size={12} />
        {isBuildingRoute ? 'Building route…' : 'Open in Maps'}
      </button>

      <button
        onClick={onAddCalendar}
        disabled={
          isCreatingEvent || itinerary.places.length === 0 || isCheckingStatus || !isConnected
        }
        className="text-xs px-3 py-1.5 rounded-full border border-violet-500/40 text-violet-300 hover:bg-violet-500/10 transition-colors disabled:opacity-60 inline-flex items-center gap-1"
      >
        <CalendarPlus size={12} />
        {isCreatingEvent ? 'Creating event…' : 'Add to Calendar'}
      </button>
    </div>
  );
}
