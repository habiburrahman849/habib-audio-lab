import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Habib Audio Studio",
  description: "Transform text into lifelike speech in seconds.",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body suppressHydrationWarning className="min-h-screen bg-gray-50 flex flex-col antialiased font-sans text-gray-900">
        {children}
      </body>
    </html>
  );
}