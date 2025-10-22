import styles from './Header.module.css';

function Header({ tokenStats }) {
  return (
    <div className={styles.header}>
      <h1 className={styles.title}>
        💬 Jimmy GPT
      </h1>

      <div className={styles.tokenStats}>
        <div className={styles.statsContent}>
          <span className={styles.inputTokens}>Input: {tokenStats.total_input}</span>
          <span className={styles.outputTokens}>Output: {tokenStats.total_output}</span>
          <span className={styles.totalTokens}>Total: {tokenStats.total_tokens}</span>
        </div>
      </div>
    </div>
  );
}

export default Header;