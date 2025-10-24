import { marked } from "marked";
import styles from './MessageItem.module.css';

function formatToolResult(content) {
  const toolCallPattern = /\[TOOL_CALLS_COMPLETE]\[TOOL_RESULT]({.*?})\[\/TOOL_RESULT]/s;
  const match = content.match(toolCallPattern);

  if (!match) return content;

  try {
    const result = JSON.parse(match[1]);

    if (result.success && result.data && result.data.content && result.data.content[0]) {
      const innerData = JSON.parse(result.data.content[0].text);

      // Handle database query results
      if (innerData.data && innerData.data.rows && Array.isArray(innerData.data.rows)) {
        const rows = innerData.data.rows;
        const rowCount = innerData.rowCount || rows.length;
        const executionTime = innerData.executionTime || 'N/A';

        let formatted = `**Query Result (${rowCount} rows, execution time: ${executionTime})**\n\n`;

        if (rows.length > 0) {
          const headers = Object.keys(rows[0]);
          formatted += '| ' + headers.join(' | ') + ' |\n';
          formatted += '| ' + headers.map(() => '---').join(' | ') + ' |\n';

          rows.forEach(row => {
            formatted += '| ' + headers.map(header => row[header] || '').join(' | ') + ' |\n';
          });
        }

        return content.replace(toolCallPattern, formatted);
      }

      // Handle other structured data
      if (innerData.success !== undefined) {
        let formatted = `**Tool Result**\n\n`;
        formatted += '```json\n';
        formatted += JSON.stringify(innerData, null, 2);
        formatted += '\n```';

        return content.replace(toolCallPattern, formatted);
      }
    }

    // Fallback: format as JSON
    let formatted = `**Tool Result**\n\n`;
    formatted += '```json\n';
    formatted += JSON.stringify(result, null, 2);
    formatted += '\n```';

    return content.replace(toolCallPattern, formatted);

  } catch (e) {
    console.error('Error parsing tool result:', e);
    // If parsing fails, just remove the tool wrapper and show raw content
    return content.replace(toolCallPattern, match[1]);
  }
}

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
              dangerouslySetInnerHTML={{ __html: marked(formatToolResult(message.content)) }}
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