import { useSearchParams } from "react-router-dom";

export interface ControlState {
  deliveryDate: string;
  cutoffHour: number;
  fromDate: string;
  toDate: string;
  confidence: number;
}

export const useControlParams = (): [ControlState, (updater: Partial<ControlState>) => void] => {
  const [searchParams, setSearchParams] = useSearchParams();

  const deliveryDate = searchParams.get("date") || "2026-01-15";
  const cutoffHour = parseInt(searchParams.get("cutoff") || "9", 10);
  const fromDate = searchParams.get("from") || "2026-01-01";
  const toDate = searchParams.get("to") || "2026-01-31";
  const confidence = parseFloat(searchParams.get("confidence") || "0.80");

  const state: ControlState = {
    deliveryDate,
    cutoffHour: Number.isNaN(cutoffHour) ? 9 : cutoffHour,
    fromDate,
    toDate,
    confidence: Number.isNaN(confidence) ? 0.8 : confidence,
  };

  const updateState = (updater: Partial<ControlState>) => {
    const nextParams = new URLSearchParams(searchParams);
    if (updater.deliveryDate !== undefined) nextParams.set("date", updater.deliveryDate);
    if (updater.cutoffHour !== undefined) nextParams.set("cutoff", updater.cutoffHour.toString());
    if (updater.fromDate !== undefined) nextParams.set("from", updater.fromDate);
    if (updater.toDate !== undefined) nextParams.set("to", updater.toDate);
    if (updater.confidence !== undefined) nextParams.set("confidence", updater.confidence.toString());
    setSearchParams(nextParams, { replace: true });
  };

  return [state, updateState];
};
