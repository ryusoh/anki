import { parseCSVLine } from "./utils.js";

export function getSplitAdjustment(splitHistory, symbol, transactionDate) {
  let cumulative = 1.0;
  // Pre-calculate transaction timestamp outside the loop
  const txTime = new Date(transactionDate).getTime();

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

export function applyTransactionFIFO(lots, transaction, splitHistory) {
  // Bolt Optimization:
  // Instead of deeply cloning the 'lots' array on every transaction,
  // we modify it in-place. This significantly reduces intermediate object
  // allocations and Garbage Collection pressure in hot loops,
  // making performance scales much better for large datasets.
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

  const chronologicalTransactions = [...transactions].sort(
    (a, b) =>
      new Date(a.tradeDate) - new Date(b.tradeDate) ||
      a.transactionId - b.transactionId,
  );

  chronologicalTransactions.forEach((transaction) => {
    const security = transaction.security;
    const currentState = securityStates.get(security) || {
      lots: [],
      totalRealizedGain: 0,
    };

    const { lots: updatedLots, realizedGainDelta } = applyTransactionFIFO(
      currentState.lots,
      transaction,
      splitHistory,
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
  });

  const totalRealizedGain = Array.from(securityStates.values()).reduce(
    (sum, s) => sum + s.totalRealizedGain,
    0,
  );
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
