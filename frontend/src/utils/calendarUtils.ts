import Papa from 'papaparse';
import type { CalendarDay } from '../types/calendar.types';

let calendarData: CalendarDay[] = [];
let calendarLoaded = false;

/**
 * Load calendar data from CSV file
 */
export const loadCalendarData = async (): Promise<CalendarDay[]> => {
  if (calendarLoaded) {
    return calendarData;
  }

  try {
    const response = await fetch('/data/calendardata.csv');
    const csvText = await response.text();

    return new Promise((resolve, reject) => {
      Papa.parse(csvText, {
        header: true,
        skipEmptyLines: true,
        complete: (results) => {
          calendarData = results.data.map((row: any) => ({
            date: row.Date?.split(' ')[0] || '', // Extract just YYYY-MM-DD
            weekOfYear: parseInt(row['Week of Year']) || 0,
            weekRunningOrder: parseInt(row.WeekRunningOrder) || 0,
            yyMmm: row['YY-MMM'] || '',
            monthRunningOrder: parseInt(row.MonthRunningOrder) || 0,
            quarterName: row.QuarterName || '',
            quarter: parseInt(row.Quarter) || 0,
            year: parseInt(row.Year) || 0,
          }));
          calendarLoaded = true;
          resolve(calendarData);
        },
        error: (error: Error) => {
          reject(error);
        },
      });
    });
  } catch (error) {
    console.error('Error loading calendar data:', error);
    throw error;
  }
};

/**
 * Get calendar entry for a specific date
 */
export const getCalendarDay = (date: string): CalendarDay | undefined => {
  return calendarData.find((day) => day.date === date);
};

/**
 * Get min and max dates from calendar
 */
export const getCalendarDateRange = (): { minDate: string; maxDate: string } => {
  if (calendarData.length === 0) {
    return { minDate: '', maxDate: '' };
  }

  const dates = calendarData.map((day) => day.date).filter(Boolean);
  return {
    minDate: dates[0],
    maxDate: dates[dates.length - 1],
  };
};

/**
 * Filter calendar data by date range
 */
export const filterCalendarByDateRange = (
  startDate: string | null,
  endDate: string | null
): CalendarDay[] => {
  if (!startDate && !endDate) {
    return calendarData;
  }

  return calendarData.filter((day) => {
    const date = day.date;
    if (startDate && date < startDate) return false;
    if (endDate && date > endDate) return false;
    return true;
  });
};
