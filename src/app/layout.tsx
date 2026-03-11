import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "EIA Draft Copilot",
  description: "환경영향평가 초안 작성 AI 코파일럿",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko">
      <body className="min-h-screen bg-gray-50 text-gray-900 antialiased">
        <header className="border-b bg-white px-6 py-4">
          <div className="mx-auto flex max-w-7xl items-center justify-between">
            <h1 className="text-xl font-bold text-green-700">
              EIA Draft Copilot
            </h1>
            <span className="text-sm text-gray-500">
              환경영향평가 초안 작성 도우미
            </span>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
