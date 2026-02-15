"use client";

import { createContext, useContext } from "react";

export const RecordCountContext = createContext<{
  counts: Record<string, number>;
  setCount: (section: string, count: number) => void;
}>({
  counts: {},
  setCount: () => {},
});

export const useRecordCount = () => useContext(RecordCountContext);
