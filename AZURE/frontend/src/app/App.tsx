import { RouterProvider } from "react-router";
import { router } from "./routes";
import { AIAssistant } from "./components/AIAssistant";

export default function App() {
  console.log("App component rendering!");
  return (
    <>
      <RouterProvider router={router} />
      <AIAssistant />
    </>
  );
}
