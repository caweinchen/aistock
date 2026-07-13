ALTER TABLE stocks ADD COLUMN industry VARCHAR(100) DEFAULT '';

CREATE TABLE watchlist_insight_baselines (
  id INT AUTO_INCREMENT PRIMARY KEY,
  user_id INT NOT NULL,
  stock_code VARCHAR(20) NOT NULL,
  score INT NULL,
  risk_score INT NULL,
  data_completeness VARCHAR(30) NOT NULL DEFAULT 'insufficient',
  published_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  CONSTRAINT uq_watchlist_insight_baseline_user_stock UNIQUE (user_id, stock_code),
  CONSTRAINT fk_watchlist_insight_baseline_user FOREIGN KEY (user_id) REFERENCES users(id),
  CONSTRAINT fk_watchlist_insight_baseline_stock FOREIGN KEY (stock_code) REFERENCES stocks(code)
);
