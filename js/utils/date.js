/**
 * Gets the current date in the America/New_York timezone.
 * @returns {Date} The current date in New York.
 */
export function getNyDate() {
  return new Date(
    new Date().toLocaleString("en-US", { timeZone: "America/New_York" }),
  );
}

/**
 * Checks if a given date (in NY timezone) is a trading day.
 * Trading days are Monday-Friday, excluding major US holidays.
 * @param {Date} date The date to check (should be in NY timezone).
 * @returns {boolean} True if it's a trading day.
 */
export function isWeekend(date) {
  const dayOfWeek = date.getDay();
  return dayOfWeek === 0 || dayOfWeek === 6;
}

export function isFixedHoliday(date) {
  const month = date.getMonth();
  const day = date.getDate();
  if (month === 0 && day === 1) return true;
  if (month === 6 && day === 4) return true;
  if (month === 11 && day === 25) return true;
  if (month === 5 && day === 19) return true;
  return false;
}

export function isMLKOrWashington(month, dayOfWeek, day) {
  if (month === 0 && dayOfWeek === 1 && day > 14 && day <= 21) return true;
  if (month === 1 && dayOfWeek === 1 && day > 14 && day <= 21) return true;
  return false;
}

export function isMemorialOrLabor(month, dayOfWeek, day) {
  if (month === 4 && dayOfWeek === 1 && day > 24) return true;
  if (month === 8 && dayOfWeek === 1 && day <= 7) return true;
  return false;
}

export function isThanksgiving(month, dayOfWeek, day) {
  if (month === 10 && dayOfWeek === 4 && day > 21 && day <= 28) return true;
  return false;
}

export function isFloatingHoliday(date) {
  const month = date.getMonth();
  const day = date.getDate();
  const dayOfWeek = date.getDay();

  if (isMLKOrWashington(month, dayOfWeek, day)) return true;
  if (isMemorialOrLabor(month, dayOfWeek, day)) return true;
  if (isThanksgiving(month, dayOfWeek, day)) return true;
  return false;
}

export function isGoodFriday(date) {
  const year = date.getFullYear();
  const month = date.getMonth();
  const day = date.getDate();
  const a = year % 19;
  const b = Math.floor(year / 100);
  const c = year % 100;
  const d = Math.floor(b / 4);
  const e = b % 4;
  const f = Math.floor((b + 8) / 25);
  const g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4);
  const k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const easterMonth = Math.floor((h + l - 7 * m + 114) / 31) - 1;
  const easterDay = ((h + l - 7 * m + 114) % 31) + 1;

  const easterDate = new Date(year, easterMonth, easterDay);
  const goodFridayDate = new Date(
    easterDate.getTime() - 2 * 24 * 60 * 60 * 1000,
  );

  return month === goodFridayDate.getMonth() && day === goodFridayDate.getDate();
}

/**
 * Checks if a given date (in NY timezone) is a trading day.
 * Trading days are Monday-Friday, excluding major US holidays.
 * @param {Date} date The date to check (should be in NY timezone).
 * @returns {boolean} True if it's a trading day.
 */
export function isTradingDay(date) {
  if (isWeekend(date)) return false;
  if (isFixedHoliday(date)) return false;
  if (isFloatingHoliday(date)) return false;
  if (isGoodFriday(date)) return false;
  return true;
}

/**
 * Gets the current NY date only if it's a trading day, otherwise returns null.
 * @param {Date} [dateOverride] - Optional date to check instead of current NY date
 * @returns {Date|null} The current date in New York if it's a trading day, null otherwise.
 */
export function getTradingDayDate(dateOverride = null) {
  const nyDate = dateOverride || getNyDate();
  return isTradingDay(nyDate) ? nyDate : null;
}

export function toIsoDate(date) {
  if (!(date instanceof Date) || Number.isNaN(date.getTime())) {
    return "";
  }
  return date.toISOString().split("T")[0];
}

export function parseYearFromDate(value) {
  if (!value || (typeof value !== "string" && !(value instanceof Date))) {
    return null;
  }
  if (value instanceof Date) {
    return value.getUTCFullYear();
  }
  const match = String(value).match(/^\s*(\d{4})/);
  if (!match) {
    return null;
  }
  const year = Number.parseInt(match[1], 10);
  return Number.isFinite(year) ? year : null;
}

export function parseQuarterToken(token, fallbackYear) {
  if (typeof token !== "string") {
    return null;
  }
  const explicit = token.match(/^\s*(\d{4})q([1-4])\s*$/i);
  if (explicit) {
    return {
      year: Number.parseInt(explicit[1], 10),
      quarter: Number.parseInt(explicit[2], 10),
    };
  }
  const simple = token.match(/^\s*q([1-4])\s*$/i);
  if (simple && Number.isFinite(fallbackYear)) {
    return {
      year: fallbackYear,
      quarter: Number.parseInt(simple[1], 10),
    };
  }
  return null;
}

export function resolveQuarterRange(year, quarter, mode = "full") {
  if (!Number.isFinite(year) || !Number.isFinite(quarter)) {
    return { from: null, to: null };
  }
  const startDate = new Date(Date.UTC(year, (quarter - 1) * 3, 1));
  const nextQuarter = new Date(Date.UTC(year, quarter * 3, 1));
  const endDate = new Date(nextQuarter.getTime() - 24 * 60 * 60 * 1000);

  const from = toIsoDate(startDate);
  const to = toIsoDate(endDate);

  if (mode === "start") {
    return { from, to: null };
  }
  if (mode === "end") {
    return { from: null, to };
  }
  return { from, to };
}

export function normalizeDateOnly(input) {
  if (!input) {
    return null;
  }
  const date = input instanceof Date ? new Date(input) : new Date(input);
  if (Number.isNaN(date.getTime())) {
    return null;
  }
  date.setHours(0, 0, 0, 0);
  return date;
}
