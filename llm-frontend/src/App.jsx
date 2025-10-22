import { useState, useRef } from "react";
import { marked } from "marked";
import "./App.css";

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
    <div className="app-container">
      <h1>💬 Jimmy GPT</h1>

      <div className="input-container">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type your prompt..."
          rows={3}
        />
        <button onClick={handleStream} disabled={loading}>
          {loading ? "Streaming..." : "Send"}
        </button>
      </div>

      <div className="speed-control">
        <label>Typing Speed: {typingSpeed} ms</label>
        <input
          type="range"
          min="0"
          max="200"
          step="10"
          value={typingSpeed}
          onChange={(e) => setTypingSpeed(Number(e.target.value))}
        />
      </div>

      <div className="response-container">
        {response ? (
          <div
            className="markdown-body"
            dangerouslySetInnerHTML={{ __html: response }}
          />
        ) : (
          <p className="placeholder">Response will appear here...</p>
        )}
      </div>
    </div>
  );
}

export default App;

