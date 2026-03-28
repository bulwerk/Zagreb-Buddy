'use client';

import { Navigation, CalendarPlus } from 'lucide-react';
import { Itinerary } from '@/lib/types';

interface GoogleActionsProps {
  itinerary: Itinerary;
}

function buildMapsUrl(itinerary: Itinerary): string {
  const places = itinerary.places;
  if (places.length === 0) return '';

  if (places.length === 1) {
    return `https://www.google.com/maps/search/?api=1&query=${places[0].lat},${places[0].lng}`;
  }

  const origin = `${places[0].lat},${places[0].lng}`;
  const destination = `${places[places.length - 1].lat},${places[places.length - 1].lng}`;
  const waypoints = places
    .slice(1, -1)
    .map((p) => `${p.lat},${p.lng}`)
    .join('|');

  const params = new URLSearchParams({
    api: '1',
    travelmode: 'walking',
    origin,
    destination,
  });
  if (waypoints) params.set('waypoints', waypoints);

  return `https://www.google.com/maps/dir/?${params.toString()}`;
}

function buildCalendarUrl(itinerary: Itinerary): string {
  const now = new Date();
  const start = new Date(now.getTime() + 15 * 60_000);
  const end = new Date(start.getTime() + itinerary.total_duration_min * 60_000);

  const fmt = (d: Date) =>
    d.toISOString().replace(/[-:]/g, '').replace(/\.\d{3}/, '');

  const names = itinerary.places.map((p) => p.name).join(' → ');
  const firstPlace = itinerary.places[0]?.name ?? 'Zagreb';

  const params = new URLSearchParams({
    action: 'TEMPLATE',
    text: `Zagreb Buddy: ${firstPlace}`,
    dates: `${fmt(start)}/${fmt(end)}`,
    details: `Suggested route: ${names}\n\nPlanned with Zagreb Buddy`,
    location: firstPlace,
    ctz: 'Europe/Zagreb',
  });

  return `https://calendar.google.com/calendar/render?${params.toString()}`;
}

export function GoogleActions({ itinerary }: GoogleActionsProps) {
  if (itinerary.places.length === 0) return null;

  const mapsUrl = buildMapsUrl(itinerary);
  const calendarUrl = buildCalendarUrl(itinerary);

  return (
    <div className="flex flex-wrap gap-2 pt-2">
      {itinerary.places.length >= 2 && (
        <a
          href={mapsUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="text-xs px-3 py-1.5 rounded-full border border-emerald-500/40 text-emerald-300 hover:bg-emerald-500/10 transition-colors inline-flex items-center gap-1"
        >
          <Navigation size={12} />
          Open route in Maps
        </a>
      )}

      <a
        href={calendarUrl}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs px-3 py-1.5 rounded-full border border-violet-500/40 text-violet-300 hover:bg-violet-500/10 transition-colors inline-flex items-center gap-1"
      >
        <CalendarPlus size={12} />
        Add to Calendar
      </a>
    </div>
  );
}
