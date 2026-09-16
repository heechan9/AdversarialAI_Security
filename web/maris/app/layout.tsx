import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "MARIS · 해양 AI 가상 실험실",
  description: "선박 이미지의 작은 변화가 AI 판단에 미치는 영향. 실제 Clean·FGSM 기록을 탐색하는 3D 해양 실험 공간.",
  other: {
    "codex-preview": "development",
  },
  icons: {
    icon: "/favicon.svg",
    shortcut: "/favicon.svg",
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko">
      <body className="antialiased">{children}</body>
    </html>
  );
}
