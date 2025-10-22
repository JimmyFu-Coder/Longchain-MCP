import { useState, useRef } from "react";
import { marked } from "marked";

function App() {
  const [input, setInput] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);
  const [typingSpeed, setTypingSpeed] = useState(0);
  const bufferRef = useRef("");

  const handleStream = async () => {
    setLoading(true);
    setResponse("");
    bufferRef.current = "";

    try {
      const res = await fetch("http://127.0.0.1:8000/api/llm/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt: input }),
      });

      if (!res.ok) throw new Error("Network response was not ok");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value);
          for (const char of chunk) {
            bufferRef.current += char;
            setResponse(marked(bufferRef.current));
            if (typingSpeed > 0) {
              await new Promise(resolve => setTimeout(resolve, typingSpeed));
            }
          }
        }
      }
    } catch (error) {
      console.error("❌ Stream error:", error);
      setResponse("[Error] Failed to fetch stream.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="w-[800px] p-8 min-h-screen mx-auto flex flex-col items-center text-neutral-200 bg-neutral-900">
      <h1 className="text-3xl font-bold text-cyan-400 mb-6 text-center">
        💬 Jimmy GPT
      </h1>

      {/* 输入区 */}
      <div className="w-full flex flex-col gap-2 mb-4">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your prompt..."
          rows={3}
          className="w-full p-4 bg-neutral-800 text-white border border-neutral-700 rounded-md resize-none text-base leading-snug whitespace-pre-wrap break-words"
        />
        <button
          onClick={handleStream}
          disabled={loading}
          className="bg-cyan-400 text-black font-bold py-2 rounded-md transition-colors duration-200 disabled:opacity-50 hover:bg-cyan-500"
        >
          {loading ? "Streaming..." : "Send"}
        </button>
      </div>

      {/* 打印速度控制条 */}
      <div className="w-full flex flex-col mb-4">
        <label className="text-sm text-neutral-400 mb-2">
          Typing Speed: {typingSpeed} ms
        </label>
        <input
          type="range"
          min="0"
          max="200"
          step="10"
          value={typingSpeed}
          onChange={(e) => setTypingSpeed(Number(e.target.value))}
          className="accent-cyan-400 w-full"
        />
      </div>

      {/* 响应区 */}
      <div className="w-full bg-neutral-800 p-4 min-h-[200px] max-h-[400px] rounded-md whitespace-pre-wrap break-words overflow-y-auto leading-relaxed border border-neutral-700">
        {response ? (
          <div
            className="prose prose-invert max-w-none"
            dangerouslySetInnerHTML={{ __html: response }}
          />
        ) : (
          <p className="text-neutral-500 italic">
            Response will appear here...
          </p>
        )}
      </div>
    </div>
  );
}

export default App;
