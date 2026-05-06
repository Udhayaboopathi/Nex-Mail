import Link from "next/link";
import { WifiOff } from "lucide-react";

export default function OfflinePage() {
  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-950 flex items-center justify-center p-4">
      <div className="text-center space-y-4">
        <WifiOff className="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto" />
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">You&apos;re offline</h1>
        <p className="text-gray-500 dark:text-gray-400 text-sm max-w-xs">Check your internet connection and try again.</p>
        <Link href="/" className="inline-block mt-4 px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-700 text-white text-sm font-medium">Try again</Link>
      </div>
    </div>
  );
}
