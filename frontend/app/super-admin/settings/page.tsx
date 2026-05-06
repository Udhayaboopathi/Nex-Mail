"use client";

export default function SuperAdminSettings() {
  return (
    <div className="space-y-6 max-w-2xl">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Platform Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-0.5">Global configuration</p>
      </div>
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-100 dark:border-gray-800 p-6">
        <p className="text-sm text-gray-500 dark:text-gray-400">Settings are configured via environment variables in <code className="bg-gray-100 dark:bg-gray-800 px-1.5 py-0.5 rounded text-xs">.env</code>.</p>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">Refer to the README for full configuration documentation.</p>
      </div>
    </div>
  );
}
