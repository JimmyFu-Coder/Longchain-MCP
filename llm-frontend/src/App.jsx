import { useState, useRef, useEffect } from "react";
import { marked } from "marked";

function App() {
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [typingSpeed, setTypingSpeed] = useState(0);
  const [tokenStats, setTokenStats] = useState({ total_input: 0, total_output: 0, total_tokens: 0 });
  const bufferRef = useRef("");
  const messagesEndRef = useRef(null);

  // 自动滚动到底部
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversations]);

  const handleStream = async () => {
    if (!input.trim()) return;

    setLoading(true);
    bufferRef.current = "";

    // 添加用户消息到对话历史
    const userMessage = {
      id: Date.now(),
      type: "user",
      content: input,
      timestamp: new Date().toLocaleTimeString()
    };

    setConversations(prev => [...prev, userMessage]);

    // 创建AI消息占位符
    const aiMessageId = Date.now() + 1;
    const aiMessage = {
      id: aiMessageId,
      type: "assistant",
      content: "",
      timestamp: new Date().toLocaleTimeString(),
      tokenUsage: null
    };

    setConversations(prev => [...prev, aiMessage]);
    setInput(""); // 清空输入框

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
      let fullResponse = "";
      let rawBuffer = ""; // 用于处理跨chunk的token信息

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value);
          rawBuffer += chunk;

          // 检查是否包含完整的token统计信息
          const tokenMatch = rawBuffer.match(/\[TOKEN_USAGE\]({.*?})\[\/TOKEN_USAGE\]/);
          if (tokenMatch) {
            console.log("找到token信息:", tokenMatch[1]); // 调试信息
            try {
              const tokenData = JSON.parse(tokenMatch[1]);
              console.log("解析的token数据:", tokenData); // 调试信息
              setConversations(prev =>
                prev.map(msg =>
                  msg.id === aiMessageId
                    ? { ...msg, tokenUsage: tokenData }
                    : msg
                )
              );
              // 更新总计统计
              setTokenStats(prev => {
                const newStats = {
                  total_input: prev.total_input + tokenData.input_tokens,
                  total_output: prev.total_output + tokenData.output_tokens,
                  total_tokens: prev.total_tokens + tokenData.total_tokens
                };
                console.log("更新后的总计统计:", newStats); // 调试信息
                return newStats;
              });

              // 从buffer中移除token信息
              rawBuffer = rawBuffer.replace(/\[TOKEN_USAGE\].*?\[\/TOKEN_USAGE\]/g, '');
            } catch (e) {
              console.error("Token parsing error:", e);
            }
          }

          // 处理剩余内容（移除token信息后的内容）
          if (rawBuffer && !rawBuffer.includes("[TOKEN_USAGE]")) {
            for (const char of rawBuffer) {
              fullResponse += char;
              setConversations(prev =>
                prev.map(msg =>
                  msg.id === aiMessageId
                    ? { ...msg, content: fullResponse }
                    : msg
                )
              );
              if (typingSpeed > 0) {
                await new Promise(resolve => setTimeout(resolve, typingSpeed));
              }
            }
            rawBuffer = ""; // 清空buffer
          } else if (rawBuffer && rawBuffer.includes("[TOKEN_USAGE]") && !rawBuffer.includes("[/TOKEN_USAGE]")) {
            // 如果包含不完整的token信息，保留在buffer中等待下一个chunk
            continue;
          }
        }
      }
    } catch (error) {
      console.error("❌ Stream error:", error);
      setConversations(prev =>
        prev.map(msg =>
          msg.id === aiMessageId
            ? { ...msg, content: "[Error] Failed to fetch stream." }
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  };

  // 清除所有对话
  const clearConversations = () => {
    setConversations([]);
    setTokenStats({ total_input: 0, total_output: 0, total_tokens: 0 });
  };

  // 处理Enter键发送
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleStream();
    }
  };

  return (
    <div className="w-[900px] p-6 min-h-screen mx-auto flex flex-col text-neutral-200 bg-neutral-900">
      {/* 头部 */}
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-3xl font-bold text-cyan-400">
          💬 Jimmy GPT
        </h1>

        {/* Token Statistics Display */}
        <div className="bg-neutral-800 px-4 py-2 rounded-lg border border-neutral-700">
          <div className="text-sm">
            <span className="text-green-400">Input: {tokenStats.total_input}</span>
            <span className="text-blue-400 ml-3">Output: {tokenStats.total_output}</span>
            <span className="text-yellow-400 ml-3">Total: {tokenStats.total_tokens}</span>
          </div>
        </div>
      </div>

      {/* Chat History Area */}
      <div className="flex-1 bg-neutral-800 rounded-lg border border-neutral-700 mb-4 overflow-hidden flex flex-col">
        <div className="flex justify-between items-center p-4 border-b border-neutral-700">
          <span className="text-sm text-neutral-400">Chat History</span>
          <button
            onClick={clearConversations}
            className="text-xs bg-red-600 hover:bg-red-700 px-3 py-1 rounded text-white transition-colors"
          >
            Clear Chat
          </button>
        </div>

        <div className="flex-1 p-4 overflow-y-auto min-h-0 space-y-4">
          <div className="space-y-4">
            {conversations.length === 0 ? (
              <p className="text-neutral-500 italic text-center py-8">
                Start chatting...
              </p>
            ) : (
              conversations.map((msg) => (
                <div key={msg.id} className={`flex ${msg.type === "user" ? "justify-end" : "justify-start"}`}>
                  <div className={`max-w-[80%] rounded-lg p-3 ${
                    msg.type === "user"
                      ? "bg-cyan-600 text-white"
                      : "bg-neutral-700 text-neutral-100"
                  }`}>
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-xs font-semibold">
                        {msg.type === "user" ? "🧑 You" : "🤖 Assistant"}
                      </span>
                      <span className="text-xs opacity-70">{msg.timestamp}</span>
                    </div>

                    <div className="text-sm leading-relaxed">
                      {msg.type === "assistant" ? (
                        <div
                          className="prose prose-invert prose-sm max-w-none"
                          dangerouslySetInnerHTML={{ __html: marked(msg.content) }}
                        />
                      ) : (
                        <div className="whitespace-pre-wrap">{msg.content}</div>
                      )}
                    </div>

                    {/* Token Statistics (AI messages only) */}
                    {msg.type === "assistant" && msg.tokenUsage && (
                      <div className="mt-2 pt-2 border-t border-neutral-600 text-xs text-neutral-400">
                        <span className="text-green-400">Input: {msg.tokenUsage.input_tokens}</span>
                        <span className="text-blue-400 ml-2">Output: {msg.tokenUsage.output_tokens}</span>
                        <span className="text-yellow-400 ml-2">Total: {msg.tokenUsage.total_tokens}</span>
                      </div>
                    )}
                  </div>
                </div>
              ))
            )}
            <div ref={messagesEndRef} className="h-0" />
          </div>
        </div>
      </div>

      {/* Input Area */}
      <div className="space-y-3">
        {/* Typing Speed Control */}
        <div className="flex items-center gap-4">
          <label className="text-sm text-neutral-400 whitespace-nowrap">
            Typing Speed: {typingSpeed} ms
          </label>
          <input
            type="range"
            min="0"
            max="200"
            step="10"
            value={typingSpeed}
            onChange={(e) => setTypingSpeed(Number(e.target.value))}
            className="accent-cyan-400 flex-1"
          />
        </div>

        {/* Input Box and Send Button */}
        <div className="flex gap-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
            rows={3}
            className="flex-1 p-3 bg-neutral-800 text-white border border-neutral-700 rounded-lg resize-none text-sm leading-relaxed focus:border-cyan-400 focus:outline-none"
          />
          <button
            onClick={handleStream}
            disabled={loading || !input.trim()}
            className="bg-cyan-400 text-black font-bold px-6 py-2 rounded-lg transition-colors duration-200 disabled:opacity-50 disabled:cursor-not-allowed hover:bg-cyan-500 h-fit"
          >
            {loading ? "Sending..." : "Send"}
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
