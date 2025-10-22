import { useRef, useEffect } from "react";
import MessageItem from "./MessageItem";
import styles from './ChatHistory.module.css';

function ChatHistory({ conversations, onClearConversations }) {
  const messagesEndRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [conversations]);

  return (
    <div className={styles.chatHistory}>
      <div className={styles.header}>
        <span className={styles.title}>Chat History</span>
        <button
          onClick={onClearConversations}
          className={styles.clearButton}
        >
          Clear Chat
        </button>
      </div>

      <div className={styles.messagesContainer}>
        <div className={styles.messagesContent}>
          {conversations.length === 0 ? (
            <p className={styles.emptyMessage}>
              Start chatting...
            </p>
          ) : (
            conversations.map((msg) => (
              <MessageItem key={msg.id} message={msg} />
            ))
          )}
          <div ref={messagesEndRef} className={styles.scrollAnchor} />
        </div>
      </div>
    </div>
  );
}

export default ChatHistory;