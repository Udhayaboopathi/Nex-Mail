"use client";

import { useState } from "react";
import { ChevronLeft, ChevronRight, Calendar as CalIcon } from "lucide-react";
import { cn, formatDate } from "../../lib/utils";
import type { CalendarEvent } from "../../types";

interface CalendarViewProps {
  events: CalendarEvent[];
}

function getDaysInMonth(year: number, month: number) {
  return new Date(year, month + 1, 0).getDate();
}

function getFirstDayOfMonth(year: number, month: number) {
  return new Date(year, month, 1).getDay();
}

export default function CalendarView({ events }: CalendarViewProps) {
  const today = new Date();
  const [year, setYear] = useState(today.getFullYear());
  const [month, setMonth] = useState(today.getMonth());
  const [selectedDay, setSelectedDay] = useState<number | null>(today.getDate());

  const daysInMonth = getDaysInMonth(year, month);
  const firstDay = getFirstDayOfMonth(year, month);

  const monthName = new Date(year, month).toLocaleString("default", { month: "long" });

  function prevMonth() {
    if (month === 0) { setMonth(11); setYear((y) => y - 1); } else setMonth((m) => m - 1);
    setSelectedDay(null);
  }

  function nextMonth() {
    if (month === 11) { setMonth(0); setYear((y) => y + 1); } else setMonth((m) => m + 1);
    setSelectedDay(null);
  }

  function eventsOnDay(day: number) {
    return events.filter((e) => {
      const d = new Date(e.start_at);
      return d.getFullYear() === year && d.getMonth() === month && d.getDate() === day;
    });
  }

  const selectedEvents = selectedDay ? eventsOnDay(selectedDay) : [];

  const cells = Array.from({ length: firstDay }, (_, i) => ({ day: 0, key: `e-${i}` })).concat(
    Array.from({ length: daysInMonth }, (_, i) => ({ day: i + 1, key: `d-${i + 1}` }))
  );

  // Pad to 6 rows
  while (cells.length % 7 !== 0) cells.push({ day: 0, key: `p-${cells.length}` });

  return (
    <div className="flex flex-col lg:flex-row gap-6">
      {/* Calendar grid */}
      <div className="flex-1 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <button onClick={prevMonth} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"><ChevronLeft className="w-5 h-5 text-gray-600 dark:text-gray-400" /></button>
          <h2 className="font-semibold text-gray-800 dark:text-white">{monthName} {year}</h2>
          <button onClick={nextMonth} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-800"><ChevronRight className="w-5 h-5 text-gray-600 dark:text-gray-400" /></button>
        </div>

        {/* Day headers */}
        <div className="grid grid-cols-7 mb-1">
          {["Sun","Mon","Tue","Wed","Thu","Fri","Sat"].map((d) => (
            <div key={d} className="text-center text-xs font-medium text-gray-400 dark:text-gray-500 py-1">{d}</div>
          ))}
        </div>

        {/* Days */}
        <div className="grid grid-cols-7 gap-0.5">
          {cells.map(({ day, key }) => {
            if (day === 0) return <div key={key} />;
            const isToday = day === today.getDate() && month === today.getMonth() && year === today.getFullYear();
            const isSelected = day === selectedDay;
            const dayEvents = eventsOnDay(day);
            return (
              <button
                key={key}
                onClick={() => setSelectedDay(day === selectedDay ? null : day)}
                className={cn(
                  "aspect-square flex flex-col items-center justify-start rounded-lg p-1 text-sm transition-colors",
                  isSelected ? "bg-indigo-600 text-white" : isToday ? "bg-indigo-50 dark:bg-indigo-900/30 text-indigo-700 dark:text-indigo-300 font-semibold" : "hover:bg-gray-100 dark:hover:bg-gray-800 text-gray-700 dark:text-gray-300"
                )}
              >
                <span className="text-xs">{day}</span>
                {dayEvents.length > 0 && (
                  <div className={cn("w-1.5 h-1.5 rounded-full mt-0.5", isSelected ? "bg-white" : "bg-indigo-500")} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Events panel */}
      <div className="w-full lg:w-72 bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-4">
        <h3 className="font-semibold text-gray-800 dark:text-white mb-3">
          {selectedDay ? `${monthName} ${selectedDay}` : "Events"}
        </h3>
        {selectedDay === null ? (
          <p className="text-sm text-gray-400 dark:text-gray-500">Select a day to see events.</p>
        ) : selectedEvents.length === 0 ? (
          <div className="text-center py-6">
            <CalIcon className="w-10 h-10 text-gray-200 dark:text-gray-700 mx-auto mb-2" />
            <p className="text-sm text-gray-400">No events</p>
          </div>
        ) : (
          <div className="space-y-2">
            {selectedEvents.map((e) => (
              <div key={e.id} className="p-3 rounded-lg bg-indigo-50 dark:bg-indigo-900/20 border border-indigo-100 dark:border-indigo-800">
                <p className="font-medium text-sm text-gray-800 dark:text-gray-200">{e.title}</p>
                <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
                  {formatDate(e.start_at)}
                  {e.end_at ? ` → ${formatDate(e.end_at)}` : ""}
                </p>
                {e.location && <p className="text-xs text-gray-400 mt-0.5">📍 {e.location}</p>}
                {e.description && <p className="text-xs text-gray-500 mt-1 line-clamp-2">{e.description}</p>}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
