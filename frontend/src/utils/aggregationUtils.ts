import type {
  JobHistoryItem,
  OrdersHistoryItem,
  OrderLinesHistoryItem,
  AvgProcessTimeItem,
} from '../types/job.types';
import type { AggregationLevel, CalendarDay } from '../types/calendar.types';
import { getCalendarDay } from './calendarUtils';

/**
 * Get aggregation key for a date based on aggregation level
 */
const getAggregationKey = (date: string, level: AggregationLevel, calendarDay?: CalendarDay): string => {
  if (!calendarDay) return date;

  switch (level) {
    case 'daily':
      return date;
    case 'weekly':
      return `Week ${calendarDay.weekOfYear} (${calendarDay.year})`;
    case 'monthly':
      return calendarDay.yyMmm.replace('_', ' ');
    case 'quarterly':
      return calendarDay.quarterName.replace('_', ' ');
    case 'yearly':
      return calendarDay.year.toString();
    default:
      return date;
  }
};

/**
 * Get sort key for aggregated data
 */
const getSortKey = (calendarDay: CalendarDay | undefined, level: AggregationLevel): number => {
  if (!calendarDay) return 0;

  switch (level) {
    case 'daily':
      return parseInt(calendarDay.date.replace(/-/g, ''));
    case 'weekly':
      return calendarDay.weekRunningOrder;
    case 'monthly':
      return calendarDay.monthRunningOrder;
    case 'quarterly':
      return calendarDay.year * 10 + calendarDay.quarter;
    case 'yearly':
      return calendarDay.year;
    default:
      return 0;
  }
};

/**
 * Aggregate job history data
 */
export const aggregateJobHistory = (
  data: JobHistoryItem[],
  level: AggregationLevel
): JobHistoryItem[] => {
  if (level === 'daily') return data;

  const aggregated = new Map<string, { count: number; sortKey: number; displayKey: string }>();

  data.forEach((item) => {
    const calendarDay = getCalendarDay(item.date);
    const key = getAggregationKey(item.date, level, calendarDay);
    const sortKey = getSortKey(calendarDay, level);

    const existing = aggregated.get(key);
    if (existing) {
      existing.count += item.count;
    } else {
      aggregated.set(key, {
        count: item.count,
        sortKey,
        displayKey: key,
      });
    }
  });

  return Array.from(aggregated.values())
    .sort((a, b) => a.sortKey - b.sortKey)
    .map((item) => ({
      date: item.displayKey,
      count: item.count,
    }));
};

/**
 * Aggregate orders history data
 */
export const aggregateOrdersHistory = (
  data: OrdersHistoryItem[],
  level: AggregationLevel
): OrdersHistoryItem[] => {
  if (level === 'daily') return data;

  const aggregated = new Map<string, { total_orders: number; sortKey: number; displayKey: string }>();

  data.forEach((item) => {
    const calendarDay = getCalendarDay(item.date);
    const key = getAggregationKey(item.date, level, calendarDay);
    const sortKey = getSortKey(calendarDay, level);

    const existing = aggregated.get(key);
    if (existing) {
      existing.total_orders += item.total_orders;
    } else {
      aggregated.set(key, {
        total_orders: item.total_orders,
        sortKey,
        displayKey: key,
      });
    }
  });

  return Array.from(aggregated.values())
    .sort((a, b) => a.sortKey - b.sortKey)
    .map((item) => ({
      date: item.displayKey,
      total_orders: item.total_orders,
    }));
};

/**
 * Aggregate order lines history data
 */
export const aggregateOrderLinesHistory = (
  data: OrderLinesHistoryItem[],
  level: AggregationLevel
): OrderLinesHistoryItem[] => {
  if (level === 'daily') return data;

  const aggregated = new Map<string, { total_order_lines: number; sortKey: number; displayKey: string }>();

  data.forEach((item) => {
    const calendarDay = getCalendarDay(item.date);
    const key = getAggregationKey(item.date, level, calendarDay);
    const sortKey = getSortKey(calendarDay, level);

    const existing = aggregated.get(key);
    if (existing) {
      existing.total_order_lines += item.total_order_lines;
    } else {
      aggregated.set(key, {
        total_order_lines: item.total_order_lines,
        sortKey,
        displayKey: key,
      });
    }
  });

  return Array.from(aggregated.values())
    .sort((a, b) => a.sortKey - b.sortKey)
    .map((item) => ({
      date: item.displayKey,
      total_order_lines: item.total_order_lines,
    }));
};

/**
 * Aggregate average process time data
 * For this metric, we calculate the average within each aggregation period
 */
export const aggregateAvgProcessTime = (
  data: AvgProcessTimeItem[],
  level: AggregationLevel
): AvgProcessTimeItem[] => {
  if (level === 'daily') return data;

  const aggregated = new Map<
    string,
    {
      totalDuration: number;
      count: number;
      sortKey: number;
      displayKey: string;
      jobIds: Set<number>;
    }
  >();

  data.forEach((item) => {
    const calendarDay = getCalendarDay(item.date);
    const key = getAggregationKey(item.date, level, calendarDay);
    const sortKey = getSortKey(calendarDay, level);

    const duration = item.duration_seconds ?? 0;

    const existing = aggregated.get(key);
    if (existing) {
      existing.totalDuration += duration;
      existing.count += 1;
      existing.jobIds.add(item.job_id);
    } else {
      aggregated.set(key, {
        totalDuration: duration,
        count: 1,
        sortKey,
        displayKey: key,
        jobIds: new Set([item.job_id]),
      });
    }
  });

  return Array.from(aggregated.values())
    .sort((a, b) => a.sortKey - b.sortKey)
    .map((item) => ({
      date: item.displayKey,
      job_id: 0, // Aggregated, so no single job_id
      duration_seconds: item.totalDuration / item.count, // Average duration
    }));
};

/**
 * Filter data by date range
 */
export const filterByDateRange = <T extends { date: string }>(
  data: T[],
  startDate: string | null,
  endDate: string | null
): T[] => {
  if (!startDate && !endDate) return data;

  return data.filter((item) => {
    if (startDate && item.date < startDate) return false;
    if (endDate && item.date > endDate) return false;
    return true;
  });
};
