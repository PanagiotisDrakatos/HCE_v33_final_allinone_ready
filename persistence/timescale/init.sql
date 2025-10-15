CREATE EXTENSION IF NOT EXISTS timescaledb;
CREATE TABLE IF NOT EXISTS market_signals (
  run_id TEXT NOT NULL,
  ts TIMESTAMPTZ NOT NULL,
  symbol TEXT NOT NULL,
  metric TEXT NOT NULL,
  value DOUBLE PRECISION,
  label TEXT,
  PRIMARY KEY (run_id, ts, symbol, metric)
);
SELECT create_hypertable('market_signals', 'ts', if_not_exists => TRUE);
