import { Sidebar } from "@/components/Sidebar";
import { ChatView } from "@/components/ChatView";

export default function App() {
  return (
    <div className="flex h-screen overflow-hidden bg-ink-50">
      <Sidebar />
      <ChatView />
    </div>
  );
}
