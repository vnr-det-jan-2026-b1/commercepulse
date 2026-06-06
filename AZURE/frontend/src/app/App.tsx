import { RouterProvider } from "react-router";
import { router } from "./routes";
import { AIAssistant } from "./components/AIAssistant";
import { Analytics } from "@vercel/analytics/react";
import { ThemeProvider } from "next-themes";

export default function App() {
  console.log("App component rendering!");
  return (
    <ThemeProvider attribute="class" defaultTheme="system" enableSystem>
      <RouterProvider router={router} />
      <AIAssistant />
      <Analytics />
    </ThemeProvider>
  );
}
