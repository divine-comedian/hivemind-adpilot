import type { Metadata } from "next";
import localFont from "next/font/local";
import "./globals.css";

const display = localFont({
  src: "../../fonts/EB_Garamond/EBGaramond-VariableFont_wght.ttf",
  variable: "--font-display",
  display: "swap",
});

const body = localFont({
  src: "../../fonts/Geist/Geist-VariableFont_wght.ttf",
  variable: "--font-body",
  display: "swap",
});

const mono = localFont({
  src: "../../fonts/Raleway/Raleway-VariableFont_wght.ttf",
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "AdPilot",
  description: "Hivemind-powered paid ads operator",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${body.variable} ${mono.variable} antialiased`}>
        {children}
      </body>
    </html>
  );
}
