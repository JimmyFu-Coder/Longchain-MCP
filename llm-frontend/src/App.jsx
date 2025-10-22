import { useState, useRef } from "react";
import Header from "./components/Header";
import ChatHistory from "./components/ChatHistory";
import InputArea from "./components/InputArea";
import FileUpload from "./components/FileUpload";
import styles from "./App.module.css";

function App() {
  const [input, setInput] = useState("");
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [typingSpeed, setTypingSpeed] = useState(0);
  const [tokenStats, setTokenStats] = useState({ total_input: 0, total_output: 0, total_tokens: 0 });
  const bufferRef = useRef("");

  const handleStream = async () => {
    if (!input.trim()) return;

    setLoading(true);
    bufferRef.current = "";

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

  const clearConversations = () => {
    setConversations([]);
    setTokenStats({ total_input: 0, total_output: 0, total_tokens: 0 });
  };

  const handleFileProcessed = async (processedFile) => {
    // Add file upload system message to conversation
    const fileMessage = {
      id: Date.now(),
      type: "system",
      content: `📎 File uploaded: ${processedFile.fileName}\n\nFile content summary:\n${processedFile.content.substring(0, 300)}...`,
      timestamp: new Date().toLocaleTimeString(),
      fileInfo: processedFile
    };

    setConversations(prev => [...prev, fileMessage]);

    // Auto-send file content to AI for analysis
    const prompt = `Please analyze the following file content:\n\nFile: ${processedFile.fileName}\nType: ${processedFile.fileType}\nContent:\n${processedFile.content}`;

    setLoading(true);
    bufferRef.current = "";

    // Create AI message placeholder
    const aiMessageId = Date.now() + 1;
    const aiMessage = {
      id: aiMessageId,
      type: "assistant",
      content: "",
      timestamp: new Date().toLocaleTimeString(),
      tokenUsage: null
    };

    setConversations(prev => [...prev, aiMessage]);

    try {
      const res = await fetch("http://127.0.0.1:8000/api/llm/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ prompt }),
      });

      if (!res.ok) throw new Error("Network response was not ok");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let done = false;
      let fullResponse = "";
      let rawBuffer = "";

      while (!done) {
        const { value, done: doneReading } = await reader.read();
        done = doneReading;
        if (value) {
          const chunk = decoder.decode(value);
          rawBuffer += chunk;

          // Handle token usage info
          const tokenMatch = rawBuffer.match(/\[TOKEN_USAGE\]({.*?})\[\/TOKEN_USAGE\]/);
          if (tokenMatch) {
            try {
              const tokenData = JSON.parse(tokenMatch[1]);
              setConversations(prev =>
                prev.map(msg =>
                  msg.id === aiMessageId
                    ? { ...msg, tokenUsage: tokenData }
                    : msg
                )
              );
              setTokenStats(prev => ({
                total_input: prev.total_input + tokenData.input_tokens,
                total_output: prev.total_output + tokenData.output_tokens,
                total_tokens: prev.total_tokens + tokenData.total_tokens
              }));

              rawBuffer = rawBuffer.replace(/\[TOKEN_USAGE\].*?\[\/TOKEN_USAGE\]/g, '');
            } catch (e) {
              console.error("Token parsing error:", e);
            }
          }

          // Process content
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
            rawBuffer = "";
          } else if (rawBuffer && rawBuffer.includes("[TOKEN_USAGE]") && !rawBuffer.includes("[/TOKEN_USAGE]")) {
            continue;
          }
        }
      }
    } catch (error) {
      console.error("❌ File analysis error:", error);
      setConversations(prev =>
        prev.map(msg =>
          msg.id === aiMessageId
            ? { ...msg, content: "[Error] Failed to analyze file content." }
            : msg
        )
      );
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className={styles.container}>
      <Header tokenStats={tokenStats} />

      <FileUpload onFileProcessed={handleFileProcessed} />

      <ChatHistory
        conversations={conversations}
        onClearConversations={clearConversations}
      />

      <InputArea
        input={input}
        setInput={setInput}
        typingSpeed={typingSpeed}
        setTypingSpeed={setTypingSpeed}
        loading={loading}
        onSubmit={handleStream}
      />
    </div>
  );
}

export default App;
