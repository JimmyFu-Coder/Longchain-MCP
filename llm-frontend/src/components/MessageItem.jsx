import { marked } from "marked";
import styles from './MessageItem.module.css';

function MessageItem({ message }) {
  const isUser = message.type === "user";
  const isSystem = message.type === "system";

  return (
    <div className={`${styles.messageContainer} ${
      isUser ? styles.userMessage :
      isSystem ? styles.systemMessage :
      styles.assistantMessage
    }`}>
      <div className={`${styles.messageBubble} ${
        isUser ? styles.userBubble :
        isSystem ? styles.systemBubble :
        styles.assistantBubble
      }`}>
        <div className={styles.messageHeader}>
          <span className={styles.messageAuthor}>
            {isUser ? "🧑 You" :
             isSystem ? "📎 System" :
             "🤖 Assistant"}
          </span>
          <span className={styles.messageTimestamp}>{message.timestamp}</span>
        </div>

        <div className={styles.messageContent}>
          {isUser ? (
            <div className={styles.userContent}>{message.content}</div>
          ) : isSystem ? (
            <div className={styles.systemContent}>{message.content}</div>
          ) : (
            <div
              className={styles.assistantContent}
              dangerouslySetInnerHTML={{ __html: marked(message.content) }}
            />
          )}
        </div>

        {!isUser && !isSystem && message.tokenUsage && (
          <div className={styles.tokenUsage}>
            <span className={styles.inputTokens}>Input: {message.tokenUsage.input_tokens}</span>
            <span className={styles.outputTokens}>Output: {message.tokenUsage.output_tokens}</span>
            <span className={styles.totalTokens}>Total: {message.tokenUsage.total_tokens}</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default MessageItem;