import "@/style/globals.scss";
import { StoreProvider } from "@/store/StoreProvider";

export const metadata = {
    title: "JobPilot",
    description: "Personal agentic job-search co-pilot",
};

export default function RootLayout({ children }) {
    return (
        <html lang="en">
            <head>
                <link rel="preconnect" href="https://fonts.googleapis.com" />
                <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
                <link
                    href="https://fonts.googleapis.com/css2?family=Noto+Sans+JP:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap"
                    rel="stylesheet"
                />
            </head>
            {/* Extensions such as Grammarly add attributes to <body> before React
                hydrates, which it then reports as a mismatch. This suppresses that one
                element's own attributes; everything inside still reports normally. */}
            <body suppressHydrationWarning>
                <StoreProvider>{children}</StoreProvider>
            </body>
        </html>
    );
}
