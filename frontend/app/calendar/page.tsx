"use client";

import { useEffect, useState } from "react";
import CalendarView from "../../components/calendar/CalendarView";
import { calendarApi } from "../../lib/api";
import type { CalendarEvent } from "../../types";

export default function CalendarPage() {
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    calendarApi.list().then(setEvents).catch(() => undefined).finally(() => setLoading(false));
  }, []);

  return (
    <main className="p-6">
      {loading && <p className="mb-3 text-sm text-slate-500 dark:text-slate-400">Loading events…</p>}
      <CalendarView events={events} />
    </main>
  );
}
