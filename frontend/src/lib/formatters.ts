/**
 * Display formatters for power (MW), percentages, and UTC timestamps.
 */

export function formatMW(val: number | null | undefined, signed: boolean = false): string {
  if (val === null || val === undefined || Number.isNaN(val)) {
    return "—";
  }
  const rounded = Math.round(val);
  const formatted = new Intl.NumberFormat("en-GB").format(rounded);
  if (signed && rounded > 0) {
    return `+${formatted} MW`;
  }
  return `${formatted} MW`;
}

export function formatMWDecimal(val: number | null | undefined, decimals: number = 1): string {
  if (val === null || val === undefined || Number.isNaN(val)) {
    return "—";
  }
  const formatted = new Intl.NumberFormat("en-GB", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(val);
  return `${formatted} MW`;
}

export function formatPct(val: number | null | undefined, decimals: number = 1): string {
  if (val === null || val === undefined || Number.isNaN(val)) {
    return "—";
  }
  return `${val.toFixed(decimals)}%`;
}

export function formatRatio(val: number | null | undefined): string {
  if (val === null || val === undefined || Number.isNaN(val)) {
    return "—";
  }
  return `${val.toFixed(2)}×`;
}

export function formatHour(hour: number): string {
  return `${hour.toString().padStart(2, "0")}:00`;
}

export function formatHourUTC(hour: number): string {
  return `${hour.toString().padStart(2, "0")}:00 UTC`;
}

export function formatDate(dateStr: string): string {
  if (!dateStr) return "—";
  const parts = dateStr.split("-");
  if (parts.length === 3) {
    const months = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    const monthIdx = parseInt(parts[1], 10) - 1;
    const day = parseInt(parts[2], 10);
    return `${day} ${months[monthIdx]} ${parts[0]}`;
  }
  return dateStr;
}

export function formatDateTimeUTC(isoStr: string): string {
  if (!isoStr) return "—";
  try {
    const d = new Date(isoStr);
    const day = d.getUTCDate();
    const months = [
      "Jan", "Feb", "Mar", "Apr", "May", "Jun",
      "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    ];
    const month = months[d.getUTCMonth()];
    const hour = d.getUTCHours().toString().padStart(2, "0");
    const min = d.getUTCMinutes().toString().padStart(2, "0");
    return `${day} ${month} ${hour}:${min} UTC`;
  } catch {
    return isoStr;
  }
}

export function formatAgeHours(hours: number | null | undefined): string {
  if (hours === null || hours === undefined) return "—";
  return `${hours.toFixed(1)}h`;
}
