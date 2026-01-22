import { useState } from 'react';
import { useTranslation } from 'react-i18next';
import { format } from 'date-fns';
import { Calendar as CalendarIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Calendar } from '@/components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import type { AggregationLevel, DateRange } from '../types/calendar.types';
import { cn } from '@/lib/utils';

interface DateFilterControlsProps {
  dateRange: DateRange;
  aggregationLevel: AggregationLevel;
  onDateRangeChange: (range: DateRange) => void;
  onAggregationLevelChange: (level: AggregationLevel) => void;
}

export const DateFilterControls = ({
  dateRange,
  aggregationLevel,
  onDateRangeChange,
  onAggregationLevelChange,
}: DateFilterControlsProps) => {
  const { t } = useTranslation(['history', 'common']);
  const [startDateOpen, setStartDateOpen] = useState(false);
  const [endDateOpen, setEndDateOpen] = useState(false);

  const handleStartDateSelect = (date: Date | undefined) => {
    onDateRangeChange({
      ...dateRange,
      startDate: date ? format(date, 'yyyy-MM-dd') : null,
    });
    setStartDateOpen(false);
  };

  const handleEndDateSelect = (date: Date | undefined) => {
    onDateRangeChange({
      ...dateRange,
      endDate: date ? format(date, 'yyyy-MM-dd') : null,
    });
    setEndDateOpen(false);
  };

  const handleClearDates = () => {
    onDateRangeChange({ startDate: null, endDate: null });
  };

  return (
    <Card className="shadow-lg border border-border mb-6" style={{ backgroundColor: '#fcfcfd' }}>
      <CardContent className="pt-6">
        <div className="flex flex-wrap items-center gap-8">
          {/* Aggregation Level Selector */}
          <div className="flex items-center gap-2">
            <label className="text-sm font-semibold whitespace-nowrap">{t('history:filters.viewBy')}</label>
            <Select value={aggregationLevel} onValueChange={(value) => onAggregationLevelChange(value as AggregationLevel)}>
              <SelectTrigger className="w-[140px] bg-white">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="daily">{t('history:filters.daily')}</SelectItem>
                <SelectItem value="weekly">{t('history:filters.weekly')}</SelectItem>
                <SelectItem value="monthly">{t('history:filters.monthly')}</SelectItem>
                <SelectItem value="quarterly">{t('history:filters.quarterly')}</SelectItem>
                <SelectItem value="yearly">{t('history:filters.yearly')}</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Vertical Separator */}
          <div className="h-10 w-px bg-gray-400" />

          {/* Date Range Pickers */}
          <div className="flex items-center gap-4">
            <label className="text-sm font-semibold whitespace-nowrap">{t('history:filters.dateRange')}</label>

            {/* Start Date Picker */}
            <Popover open={startDateOpen} onOpenChange={setStartDateOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    'w-[160px] justify-start text-left font-normal bg-white',
                    !dateRange.startDate && 'text-muted-foreground'
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {dateRange.startDate ? format(new Date(dateRange.startDate), 'MMM dd, yyyy') : t('history:filters.startDate')}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0 bg-white" align="start">
                <Calendar
                  mode="single"
                  selected={dateRange.startDate ? new Date(dateRange.startDate) : undefined}
                  onSelect={handleStartDateSelect}
                  initialFocus
                />
              </PopoverContent>
            </Popover>

            <span className="text-sm text-muted-foreground">{t('history:filters.to')}</span>

            {/* End Date Picker */}
            <Popover open={endDateOpen} onOpenChange={setEndDateOpen}>
              <PopoverTrigger asChild>
                <Button
                  variant="outline"
                  className={cn(
                    'w-[160px] justify-start text-left font-normal bg-white',
                    !dateRange.endDate && 'text-muted-foreground'
                  )}
                >
                  <CalendarIcon className="mr-2 h-4 w-4" />
                  {dateRange.endDate ? format(new Date(dateRange.endDate), 'MMM dd, yyyy') : t('history:filters.endDate')}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0 bg-white" align="start">
                <Calendar
                  mode="single"
                  selected={dateRange.endDate ? new Date(dateRange.endDate) : undefined}
                  onSelect={handleEndDateSelect}
                  initialFocus
                />
              </PopoverContent>
            </Popover>
          </div>

          {/* Clear Button */}
          {(dateRange.startDate || dateRange.endDate) && (
            <Button
              variant="outline"
              size="sm"
              onClick={handleClearDates}
              className="bg-white"
            >
              {t('history:filters.clearDates')}
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  );
};
