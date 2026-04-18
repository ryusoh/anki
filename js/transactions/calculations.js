import { parseCSVLine } from "./utils.js";

// Helper to pre-process split history for O(1) lookups
export function buildSplitDictionary(splitHistory) {
  if (!Array.isArray(splitHistory)) return new Map();
  const dict = new Map();
  for (let i = 0; i < splitHistory.length; i += 1) {
    const split = splitHistory[i];
    if (!split || !split.symbol || !split.splitDate) continue;
    const time = new Date(split.splitDate).getTime();
    if (!Number.isNaN(time)) {
      let symbolSplits = dict.get(split.symbol);
      if (!symbolSplits) {
        symbolSplits = [];
        dict.set(split.symbol, symbolSplits);
      }
      symbolSplits.push({ time, multiplier: split.splitMultiplier || 1.0 });
    }
  }
  return dict;
}

export function getSplitAdjustment(splitHistory, symbol, transactionDate) {
  let cumulative = 1.0;
  // Bolt Optimization:
  // Instead of an O(N) scan over the entire splitHistory array for every transaction,
  // we use a Map or pre-process if passed an array. If the caller passes the
  // pre-processed Map, it becomes O(K) where K is just the splits for one symbol.
  const txTime = new Date(transactionDate).getTime();

  let splits = null;
  if (splitHistory instanceof Map) {
    splits = splitHistory.get(symbol);
  } else if (Array.isArray(splitHistory)) {
    // Fallback if not pre-processed
    for (let i = 0; i < splitHistory.length; i += 1) {
      const split = splitHistory[i];
      if (
        split.symbol === symbol &&
        new Date(split.splitDate).getTime() > txTime
      ) {
        cumulative *= split.splitMultiplier;
      }
    }
    return cumulative;
  }

  if (splits) {
    for (let i = 0; i < splits.length; i += 1) {
      if (splits[i].time > txTime) {
        cumulative *= splits[i].multiplier;
      }
    }
  }

  return cumulative;
}

export function applyTransactionFIFO(lots, transaction, splitHistory) {
  // Bolt Optimization:
  // 1. Instead of deeply cloning the 'lots' array on every transaction,
  // we modify it in-place. This significantly reduces intermediate object
  // allocations and Garbage Collection pressure in hot loops,
  // making performance scales much better for large datasets.
  // 2. Used a pre-processed Map for splitHistory in getSplitAdjustment,
  // converting O(N) array scans into O(1) lookups during hot transaction processing loops.
  let realizedGainDelta = 0;

  const quantity = parseFloat(transaction.quantity);
  const price = parseFloat(transaction.price);
  if (!Number.isFinite(quantity) || !Number.isFinite(price) || quantity <= 0) {
    return { lots, realizedGainDelta: 0 };
  }

  const isBuy = transaction.orderType.toLowerCase() === "buy";
  const adjustment = getSplitAdjustment(
    splitHistory,
    transaction.security,
    transaction.tradeDate,
  );

  if (isBuy) {
    const adjustedQuantity = quantity * adjustment;
    const adjustedPrice = price / adjustment;
    lots.push({ qty: adjustedQuantity, price: adjustedPrice });
  } else {
    const adjustedSellQuantity = quantity * adjustment;
    let sellQty = adjustedSellQuantity;
    let costOfSoldShares = 0;

    while (sellQty > 0 && lots.length > 0) {
      const lot = lots[0];
      const qtyFromLot = Math.min(sellQty, lot.qty);

      costOfSoldShares += qtyFromLot * lot.price;
      lot.qty -= qtyFromLot;
      sellQty -= qtyFromLot;

      if (lot.qty < 1e-8) {
        lots.shift();
      }
    }
    const proceeds = quantity * price;
    realizedGainDelta = proceeds - costOfSoldShares;
  }

  return { lots, realizedGainDelta };
}

export function computeRunningTotals(transactions, splitHistory) {
  const securityStates = new Map();
  const runningTotalsById = new Map();
  let cumulativeNetAmount = 0;

  const splitDict =
    splitHistory instanceof Map
      ? splitHistory
      : buildSplitDictionary(splitHistory);

  // Bolt Optimization: Replace .map().sort().map() chain with a single pre-allocated array loop
  // and in-place .sort() to minimize intermediate object allocations and GC pressure.
  const len = transactions.length;
  const chronologicalTransactions = new Array(len);
  for (let i = 0; i < len; i++) {
    const t = transactions[i];
    chronologicalTransactions[i] = {
      t,
      parsedDate: new Date(t.tradeDate).getTime(),
    };
  }
  chronologicalTransactions.sort(
    (a, b) =>
      a.parsedDate - b.parsedDate || a.t.transactionId - b.t.transactionId,
  );
  for (let i = 0; i < len; i++) {
    chronologicalTransactions[i] = chronologicalTransactions[i].t;
  }

  for (let idx = 0; idx < len; idx++) {
    const transaction = chronologicalTransactions[idx];
    const security = transaction.security;
    const currentState = securityStates.get(security) || {
      lots: [],
      totalRealizedGain: 0,
    };

    const { lots: updatedLots, realizedGainDelta } = applyTransactionFIFO(
      currentState.lots,
      transaction,
      splitDict,
    );

    const newState = {
      lots: updatedLots,
      totalRealizedGain: currentState.totalRealizedGain + realizedGainDelta,
    };
    securityStates.set(security, newState);

    let totalShares = 0;
    for (let i = 0; i < newState.lots.length; i++) {
      totalShares += newState.lots[i].qty;
    }
    const netAmount = Number.parseFloat(transaction.netAmount);
    const normalizedNetAmount = Number.isFinite(netAmount) ? netAmount : 0;
    cumulativeNetAmount += normalizedNetAmount;

    runningTotalsById.set(transaction.transactionId, {
      shares: totalShares,
      amount: cumulativeNetAmount,
      portfolio: cumulativeNetAmount,
    });
  }

  // Bolt Optimization: Replace Array.from().reduce() with a for...of loop
  // to avoid intermediate array allocations and GC pressure.
  let totalRealizedGain = 0;
  for (const s of securityStates.values()) {
    totalRealizedGain += s.totalRealizedGain;
  }
  runningTotalsById.totalRealizedGain = totalRealizedGain;

  return runningTotalsById;
}

export function parseCSV(csvText) {
  const lines = csvText.trim().split("\n");
  const transactions = [];
  for (let i = 1; i < lines.length; i += 1) {
    const values = parseCSVLine(lines[i]);
    if (values.length >= 5) {
      const quantity = parseFloat(values[3]) || 0;
      const price = parseFloat(values[4]) || 0;
      transactions.push({
        tradeDate: values[0],
        orderType: values[1],
        security: values[2],
        quantity: values[3],
        price: values[4],
        netAmount: (
          quantity *
          price *
          (values[1].toLowerCase() === "sell" ? -1 : 1)
        ).toString(),
        transactionId: i - 1,
      });
    }
  }
  return transactions;
}
