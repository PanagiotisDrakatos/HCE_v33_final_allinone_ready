CREATE DATABASE IF NOT EXISTS hce;
CREATE TABLE IF NOT EXISTS hce.market_signals
(
  run_id String,
  ts DateTime64(3, 'UTC'),
  symbol String,
  metric String,
  value Float64,
  label String,
  PRIMARY KEY (run_id, ts, symbol, metric)
) ENGINE = MergeTree
ORDER BY (run_id, ts, symbol, metric);
