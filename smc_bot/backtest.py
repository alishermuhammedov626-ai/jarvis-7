"""Event-driven backtester.

Replays 1m candles (CSV: ts,open,high,low,close,volume) through the very same
``SmcScalperBot.step`` used live, with :class:`PaperExchange` filling orders.

    python -m smc_bot.backtest --csv DOGE=data/doge_1m.csv --csv PEPE=data/pepe_1m.csv
"""
from __future__ import annotations

import argparse
import logging
from datetime import timedelta

import pandas as pd

from .bot import SmcScalperBot
from .config import BotConfig, load_config
from .data.feed import HistoricalDataSource
from .execution.exchange import PaperExchange
from .models import MarketSpec, TradeState


def load_csv(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    ts_col = "ts" if "ts" in df.columns else df.columns[0]
    if pd.api.types.is_numeric_dtype(df[ts_col]):
        unit = "ms" if df[ts_col].iloc[0] > 1e11 else "s"
        df[ts_col] = pd.to_datetime(df[ts_col], unit=unit, utc=True)
    else:
        df[ts_col] = pd.to_datetime(df[ts_col], utc=True)
    df = df.rename(columns={ts_col: "ts"}).set_index("ts").sort_index()
    return df[["open", "high", "low", "close", "volume"]].astype(float)


def run_backtest(cfg: BotConfig, base: dict[str, pd.DataFrame], step_tf: str = "5m",
                 warmup_hours: int = 48) -> dict:
    cfg.symbols = list(base.keys())
    cfg.state_dir = ""  # no persistence
    data = HistoricalDataSource(base, "1m")
    specs = {s: MarketSpec(s, 1.0, 1e-8, 1.0, 5.0, 20) for s in base}
    paper = PaperExchange(cfg.exchange.paper_equity, cfg.exchange.slippage_bps, cfg.exchange.fee_bps, specs)
    bot = SmcScalperBot(cfg, data, paper)

    start = min(df.index[0] for df in base.values()) + timedelta(hours=warmup_hours)
    end = max(df.index[-1] for df in base.values())
    step = {"1m": 1, "5m": 5}[step_tf]
    equity_curve = []
    now = start.ceil(f"{step}min")
    while now <= end:
        # fills happen on the 1m candles that closed since the previous step
        for t in bot.manager.active():
            window = base[t.symbol][(base[t.symbol].index >= now - timedelta(minutes=step)) &
                                    (base[t.symbol].index < now)]
            for ts, row in window.iterrows():
                paper.process_candle(t.symbol, float(row["high"]), float(row["low"]), ts)
        bot.step(now)
        equity_curve.append((now, paper.equity()))
        now += timedelta(minutes=step)

    trades = [t for t in bot.manager.trades.values() if t.state is TradeState.CLOSED]
    wins = [t for t in trades if t.realized_pnl > 0]
    losses = [t for t in trades if t.realized_pnl <= 0]
    gross_win = sum(t.realized_pnl for t in wins)
    gross_loss = -sum(t.realized_pnl for t in losses)
    return {
        "trades": len(trades),
        "cancelled": sum(1 for t in bot.manager.trades.values() if t.state is TradeState.CANCELLED),
        "win_rate": len(wins) / len(trades) if trades else 0.0,
        "profit_factor": gross_win / gross_loss if gross_loss > 0 else float("inf"),
        "net_pnl": sum(t.realized_pnl for t in trades),
        "final_equity": paper.equity(),
        "equity_curve": equity_curve,
        "trade_list": trades,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=None)
    ap.add_argument("--csv", action="append", required=True, help="SYMBOL=path.csv (1m candles)")
    ap.add_argument("--warmup-hours", type=int, default=48)
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    cfg = load_config(args.config)
    base = {}
    for item in args.csv:
        sym, path = item.split("=", 1)
        base[sym] = load_csv(path)
    res = run_backtest(cfg, base, warmup_hours=args.warmup_hours)
    print(f"trades={res['trades']} cancelled={res['cancelled']} win_rate={res['win_rate']:.1%} "
          f"PF={res['profit_factor']:.2f} net={res['net_pnl']:.2f} equity={res['final_equity']:.2f}")
    for t in res["trade_list"]:
        print(f"  {t.created_at:%Y-%m-%d %H:%M} {t.symbol:6} {t.side.value:5} entry={t.avg_entry:.8g} "
              f"sl={t.stop_loss:.8g} pnl={t.realized_pnl:+.2f} ({t.close_reason})")


if __name__ == "__main__":
    main()
