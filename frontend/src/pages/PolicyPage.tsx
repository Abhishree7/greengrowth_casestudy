import { useState, useRef, useEffect } from "react";
import { Send, Quote, AlertCircle } from "lucide-react";
import { api } from "../api";
import type { PolicyAnswer } from "../types";

interface ChatHistoryMessage {
  role: string;
  content: string;
}

interface Message {
  role: "user" | "assistant";
  content: string;
  answer?: PolicyAnswer;
}

export default function PolicyPage() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend() {
    const q = input.trim();
    if (!q || loading) return;

    // Snapshot history before adding the new user message
    const history: ChatHistoryMessage[] = messages.map((m) => ({ role: m.role, content: m.content }));

    setMessages((m) => [...m, { role: "user", content: q }]);
    setInput("");
    setLoading(true);

    try {
      const answer = await api.askPolicy(q, history);
      setMessages((m) => [
        ...m,
        { role: "assistant", content: answer.answer, answer },
      ]);
    } catch {
      setMessages((m) => [
        ...m,
        {
          role: "assistant",
          content: "Failed to reach the policy service. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-8rem)]">
      <div className="mb-4">
        <h1 className="text-xl font-semibold text-gray-900">Policy Q&A</h1>
        <p className="text-sm text-gray-500 mt-0.5">
          Ask questions about Northwind Logistics travel & expense policies.
        </p>
      </div>

      {/* Chat messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="text-center py-16 text-gray-400 space-y-3">
            <Quote size={32} className="mx-auto opacity-30" />
            <p className="text-sm">Ask a question about any T&E policy.</p>
            <div className="flex flex-wrap gap-2 justify-center mt-4">
              {[
                "What is the dinner cap for solo travel?",
                "When is alcohol reimbursable?",
                "What is the lodging cap in Boston?",
                "How do client entertainment caps differ from travel caps?",
              ].map((q) => (
                <button
                  key={q}
                  onClick={() => setInput(q)}
                  className="text-xs bg-gray-100 hover:bg-gray-200 text-gray-600 px-3 py-1.5 rounded-full transition-colors"
                >
                  {q}
                </button>
              ))}
            </div>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            {msg.role === "user" ? (
              <div className="max-w-lg bg-blue-600 text-white px-4 py-2.5 rounded-2xl rounded-tr-sm text-sm">
                {msg.content}
              </div>
            ) : (
              <div className="max-w-2xl space-y-3">
                {/* Out-of-scope banner */}
                {msg.answer && !msg.answer.is_in_scope && (
                  <div className="flex items-center gap-2 bg-amber-50 border border-amber-200 rounded-lg px-3 py-2 text-xs text-amber-700">
                    <AlertCircle size={14} />
                    This question is outside the policy library scope.
                  </div>
                )}

                <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-800 leading-relaxed">
                  {msg.content}
                </div>

                {/* Citations */}
                {msg.answer && msg.answer.citations.length > 0 && (
                  <div className="space-y-2 pl-1">
                    {msg.answer.citations.map((c, j) => (
                      <div
                        key={j}
                        className="bg-gray-50 border border-gray-200 rounded-lg px-3 py-2.5"
                      >
                        <div className="flex items-center gap-1.5 mb-1">
                          <Quote size={11} className="text-gray-400" />
                          <span className="text-xs font-semibold text-gray-600">
                            {c.doc_id} {c.section}
                          </span>
                        </div>
                        <p className="text-xs text-gray-500 italic leading-relaxed">
                          "{c.quoted_text}"
                        </p>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-white border border-gray-200 rounded-2xl rounded-tl-sm px-4 py-3 text-sm text-gray-400">
              Searching policies...
            </div>
          </div>
        )}

        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div className="flex gap-3 pt-3 border-t border-gray-200">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleSend()}
          placeholder="Ask about any Northwind Logistics policy..."
          className="flex-1 border border-gray-300 rounded-xl px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button
          onClick={handleSend}
          disabled={!input.trim() || loading}
          className="p-2.5 bg-blue-600 text-white rounded-xl hover:bg-blue-700 disabled:opacity-50 transition-colors"
        >
          <Send size={18} />
        </button>
      </div>
    </div>
  );
}
