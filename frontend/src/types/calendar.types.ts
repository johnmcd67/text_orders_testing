export interface CalendarDay {
  date: string; // YYYY-MM-DD format
  weekOfYear: number;
  weekRunningOrder: number; // YYYYWW
  yyMmm: string; // YY_MMM
  monthRunningOrder: number; // YYYYMM
  quarterName: string; // YYYY_QN
  quarter: number; // 1-4
  year: number;
}

export type AggregationLevel = 'daily' | 'weekly' | 'monthly' | 'quarterly' | 'yearly';

export interface DateRange {
  startDate: string | null;
  endDate: string | null;
}
