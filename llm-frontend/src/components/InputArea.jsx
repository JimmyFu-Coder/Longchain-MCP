import styles from './InputArea.module.css';

function InputArea({
  input,
  setInput,
  typingSpeed,
  setTypingSpeed,
  loading,
  onSubmit
}) {
  const handleKeyPress = (e) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      onSubmit();
    }
  };

  return (
    <div className={styles.inputArea}>
      <div className={styles.typingSpeedControl}>
        <label className={styles.speedLabel}>
          Typing Speed: {typingSpeed} ms
        </label>
        <input
          type="range"
          min="0"
          max="200"
          step="10"
          value={typingSpeed}
          onChange={(e) => setTypingSpeed(Number(e.target.value))}
          className={styles.speedSlider}
        />
      </div>

      <div className={styles.inputContainer}>
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyPress={handleKeyPress}
          placeholder="Type your message... (Enter to send, Shift+Enter for new line)"
          rows={3}
          className={styles.textarea}
        />
        <button
          onClick={onSubmit}
          disabled={loading || !input.trim()}
          className={styles.sendButton}
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}

export default InputArea;