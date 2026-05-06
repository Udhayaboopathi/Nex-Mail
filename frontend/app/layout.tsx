import type { Metadata } from "next";
import type { ReactNode } from "react";
import { ToastContainer } from "../components/ui/Toast";
import "./globals.css";

export const metadata: Metadata = {
  title: "Nex Mail",
  description: "Self-hosted email platform",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className="bg-gray-50 dark:bg-gray-950 text-gray-900 dark:text-gray-100 antialiased">
        {children}
        <ToastContainer />
      </body>
    </html>
  );
}
