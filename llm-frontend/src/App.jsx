import { useState } from "react";
import axios from "axios";
import "./App.css";

function App() {
  const [prompt, setPrompt] = useState("");
  const [response, setResponse] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!prompt.trim()) return;
    setLoading(true);
    setResponse("");
    try {
      const res = await axios.post("http://127.0.0.1:8000/api/llm/chat", {
        prompt: prompt,
      });
      setResponse(res.data.response);
    } catch (err) {
      console.error(err);
      setResponse("❌ Request failed. Please check if the backend server is running.");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="container">
      <h2>💬 Azure GPT Chat Demo</h2>
      <textarea
        placeholder="Type your message here..."
        value={prompt}
        onChange={(e) => setPrompt(e.target.value)}
        onKeyDown={handleKeyDown}
      />
      <button onClick={handleSend} disabled={loading}>
        {loading ? "Sending..." : "Send"}
      </button>
      {response && (
        <div className="response-box">
          <strong>Response:</strong>
          <div>{response}</div>
        </div>
      )}
    </div>
  );
}

export default App;

