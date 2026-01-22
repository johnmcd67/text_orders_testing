import { useState, useEffect, useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { jobsApi } from '../api/jobsApi';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Separator } from '@/components/ui/separator';
import { ArrowLeft } from 'lucide-react';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, LabelList } from 'recharts';
import { DateFilterControls } from './DateFilterControls';
import { loadCalendarData } from '../utils/calendarUtils';
import {
  filterByDateRange,
  aggregateJobHistory,
  aggregateOrdersHistory,
  aggregateOrderLinesHistory,
  aggregateAvgProcessTime,
} from '../utils/aggregationUtils';
import type { AggregationLevel, DateRange } from '../types/calendar.types';

export const History = () => {
  const navigate = useNavigate();
  const { t } = useTranslation(['history', 'common']);
  const [calendarLoaded, setCalendarLoaded] = useState(false);
  const [dateRange, setDateRange] = useState<DateRange>({ startDate: null, endDate: null });
  const [aggregationLevel, setAggregationLevel] = useState<AggregationLevel>('daily');

  const { data: historyData, isLoading, error } = useQuery({
    queryKey: ['jobHistory'],
    queryFn: jobsApi.getJobHistory,
  });

  const { data: ordersData } = useQuery({
    queryKey: ['ordersHistory'],
    queryFn: jobsApi.getOrdersHistory,
  });

  const { data: orderLinesData } = useQuery({
    queryKey: ['orderLinesHistory'],
    queryFn: jobsApi.getOrderLinesHistory,
  });

  const { data: avgProcessTimeData } = useQuery({
    queryKey: ['avgProcessTime'],
    queryFn: jobsApi.getAvgProcessTime,
  });

  // Load calendar data on mount
  useEffect(() => {
    loadCalendarData()
      .then(() => setCalendarLoaded(true))
      .catch((error) => console.error('Failed to load calendar data:', error));
  }, []);

  // Filter and aggregate history data
  const filteredHistoryData = useMemo(() => {
    if (!historyData || !calendarLoaded) return historyData;
    const filtered = filterByDateRange(historyData, dateRange.startDate, dateRange.endDate);
    return aggregateJobHistory(filtered, aggregationLevel);
  }, [historyData, dateRange, aggregationLevel, calendarLoaded]);

  // Filter and aggregate orders data
  const filteredOrdersData = useMemo(() => {
    if (!ordersData || !calendarLoaded) return ordersData;
    const filtered = filterByDateRange(ordersData, dateRange.startDate, dateRange.endDate);
    return aggregateOrdersHistory(filtered, aggregationLevel);
  }, [ordersData, dateRange, aggregationLevel, calendarLoaded]);

  // Filter and aggregate order lines data
  const filteredOrderLinesData = useMemo(() => {
    if (!orderLinesData || !calendarLoaded) return orderLinesData;
    const filtered = filterByDateRange(orderLinesData, dateRange.startDate, dateRange.endDate);
    return aggregateOrderLinesHistory(filtered, aggregationLevel);
  }, [orderLinesData, dateRange, aggregationLevel, calendarLoaded]);

  // Filter and aggregate avg process time data
  const filteredAvgProcessTimeData = useMemo(() => {
    if (!avgProcessTimeData || !calendarLoaded) return avgProcessTimeData;
    const filtered = filterByDateRange(avgProcessTimeData, dateRange.startDate, dateRange.endDate);
    return aggregateAvgProcessTime(filtered, aggregationLevel);
  }, [avgProcessTimeData, dateRange, aggregationLevel, calendarLoaded]);

  return (
    <div className="min-h-screen bg-background py-8 px-4">
      <div className="container mx-auto max-w-7xl">
        <header className="text-center mb-10">
          <h1 className="font-bold tracking-tight" style={{ fontSize: '3.375rem' }}>
            {t('history:title')}
          </h1>
        </header>

        <Separator className="mb-8" />

        <div className="mb-4">
          <Button
            onClick={() => navigate('/')}
            variant="outline"
            style={{
              height: '40px',
              minHeight: '40px',
              backgroundColor: 'white',
              color: 'black',
              fontWeight: 'bold',
              border: '1px solid #9ca3af',
            }}
            className="hover:bg-accent"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common:buttons.backToHome')}
          </Button>
        </div>

        {/* Date Filter Controls */}
        <DateFilterControls
          dateRange={dateRange}
          aggregationLevel={aggregationLevel}
          onDateRangeChange={setDateRange}
          onAggregationLevelChange={setAggregationLevel}
        />

        <div style={{ marginTop: '32px' }}>
          {isLoading && (
            <div className="text-center py-8">
              <p className="text-lg">{t('history:status.loading')}</p>
            </div>
          )}

          {error && (
            <div className="text-center py-8">
              <p className="text-lg text-red-500">{t('history:status.error')}</p>
            </div>
          )}

          {filteredHistoryData && filteredHistoryData.length === 0 && (
            <div className="text-center py-8">
              <p className="text-lg">{t('history:status.noData')}</p>
            </div>
          )}

          {filteredHistoryData && filteredHistoryData.length > 0 && (
            <div style={{ position: 'relative' }}>
              {/* Left Column - Row 1, Col 1: Completed Jobs Per Day Chart */}
              <div style={{ width: '635px', position: 'absolute', left: '0px', top: '0px' }}>
                <Card className="shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd' }}>
                <CardHeader>
                  <CardTitle className="text-xl font-bold">{t('history:charts.completedJobsPerDay')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <ResponsiveContainer width="100%" height={200}>
                    <BarChart data={filteredHistoryData}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis
                        dataKey="date"
                        angle={-45}
                        textAnchor="end"
                        height={80}
                        style={{ fontSize: '12px' }}
                      />
                      <YAxis />
                      <Tooltip />
                      <Legend />
                      <Bar dataKey="count" fill="#3b82f6" name={t('history:labels.jobsCompleted')}>
                        <LabelList dataKey="count" position="top" />
                      </Bar>
                    </BarChart>
                  </ResponsiveContainer>
                </CardContent>
              </Card>
              </div>

              {/* Left Column - Row 2, Col 1: History Details Table */}
              <div style={{ width: '635px', position: 'absolute', left: '0px', top: '240px' }}>
                <Card className="shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd' }}>
                <CardHeader>
                  <CardTitle className="text-xl font-bold">{t('history:tables.historyDetails')}</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="overflow-x-auto" style={{ height: '400px', overflowY: 'auto' }}>
                    <table className="w-full border-collapse">
                      <thead>
                        <tr className="border-b border-gray-300">
                          <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.date')}</th>
                          <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.completedJobs')}</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filteredHistoryData.map((item, index) => (
                          <tr
                            key={index}
                            className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                          >
                            <td className="py-2 px-4">{item.date}</td>
                            <td className="py-2 px-4">{item.count}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </CardContent>
              </Card>
              </div>

              {/* Left Column - Row 3, Col 1: Completed Order Lines Per Day Chart */}
              {filteredOrderLinesData && filteredOrderLinesData.length > 0 && (
                <div style={{ width: '635px', position: 'absolute', left: '0px', top: '720px' }}>
                  <Card className="shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd' }}>
                      <CardHeader>
                        <CardTitle className="text-xl font-bold">{t('history:charts.orderLinesPerDay')}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ResponsiveContainer width="100%" height={200}>
                          <BarChart data={filteredOrderLinesData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                              dataKey="date"
                              angle={-45}
                              textAnchor="end"
                              height={80}
                              style={{ fontSize: '12px' }}
                            />
                            <YAxis />
                            <Tooltip />
                            <Legend />
                            <Bar dataKey="total_order_lines" fill="#f59e0b" name={t('history:labels.totalOrderLines')}>
                              <LabelList dataKey="total_order_lines" position="top" />
                            </Bar>
                          </BarChart>
                        </ResponsiveContainer>
                      </CardContent>
                    </Card>
                </div>
              )}

              {/* Left Column - Row 4, Col 1: Order Lines Details Table */}
              {filteredOrderLinesData && filteredOrderLinesData.length > 0 && (
                <div style={{ width: '635px', position: 'absolute', left: '0px', top: '960px' }}>
                  <Card className="shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd' }}>
                      <CardHeader>
                        <CardTitle className="text-xl font-bold">{t('history:tables.orderLinesDetails')}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto" style={{ height: '400px', overflowY: 'auto' }}>
                          <table className="w-full border-collapse">
                            <thead>
                              <tr className="border-b border-gray-300">
                                <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.date')}</th>
                                <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.totalOrderLines')}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {filteredOrderLinesData.map((item, index) => (
                                <tr
                                  key={index}
                                  className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                                >
                                  <td className="py-2 px-4">{item.date}</td>
                                  <td className="py-2 px-4">{item.total_order_lines}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </CardContent>
                    </Card>
                </div>
              )}

              {/* Right Column - Row 1, Col 2: Completed Orders Per Day Chart */}
              {filteredOrdersData && filteredOrdersData.length > 0 && (
                <div style={{ width: '635px', position: 'absolute', left: '645px', top: '0px' }}>
                  <Card className="shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd' }}>
                    <CardHeader>
                      <CardTitle className="text-xl font-bold">{t('history:charts.ordersPerDay')}</CardTitle>
                    </CardHeader>
                    <CardContent>
                      <ResponsiveContainer width="100%" height={200}>
                        <BarChart data={filteredOrdersData}>
                          <CartesianGrid strokeDasharray="3 3" />
                          <XAxis
                            dataKey="date"
                            angle={-45}
                            textAnchor="end"
                            height={80}
                            style={{ fontSize: '12px' }}
                          />
                          <YAxis />
                          <Tooltip />
                          <Legend />
                          <Bar dataKey="total_orders" fill="#10b981" name={t('history:labels.totalOrders')}>
                            <LabelList dataKey="total_orders" position="top" />
                          </Bar>
                        </BarChart>
                      </ResponsiveContainer>
                    </CardContent>
                  </Card>
                </div>
              )}

              {/* Right Column - Row 2, Col 2: Orders Details Table */}
              {filteredOrdersData && filteredOrdersData.length > 0 && (
                <div style={{ width: '635px', position: 'absolute', left: '645px', top: '240px' }}>
                  <Card className="shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd' }}>
                      <CardHeader>
                        <CardTitle className="text-xl font-bold">{t('history:tables.ordersDetails')}</CardTitle>
                      </CardHeader>
                    <CardContent>
                      <div className="overflow-x-auto" style={{ height: '400px', overflowY: 'auto' }}>
                        <table className="w-full border-collapse">
                          <thead>
                            <tr className="border-b border-gray-300">
                              <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.date')}</th>
                              <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.totalOrders')}</th>
                            </tr>
                          </thead>
                          <tbody>
                            {filteredOrdersData.map((item, index) => (
                              <tr
                                key={index}
                                className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                              >
                                <td className="py-2 px-4">{item.date}</td>
                                <td className="py-2 px-4">{item.total_orders}</td>
                              </tr>
                            ))}
                          </tbody>
                        </table>
                      </div>
                    </CardContent>
                    </Card>
                </div>
              )}

              {/* Right Column - Row 3, Col 2: Average Process Time Per Job Chart */}
              {filteredAvgProcessTimeData && filteredAvgProcessTimeData.length > 0 && (() => {
                // Transform data for stacked bar chart
                const transformedData: Record<string, any>[] = [];
                const jobIds = new Set<number>();

                // Group by date and collect all job_ids, calculate total per date
                filteredAvgProcessTimeData.forEach(item => {
                  jobIds.add(item.job_id);
                  let dateEntry = transformedData.find(d => d.date === item.date);
                  if (!dateEntry) {
                    dateEntry = { date: item.date, total: 0 };
                    transformedData.push(dateEntry);
                  }
                  dateEntry[`Job ${item.job_id}`] = item.duration_seconds;
                  dateEntry.total += item.duration_seconds || 0;
                });

                // Round the totals
                transformedData.forEach(entry => {
                  entry.total = Math.round(entry.total);
                });

                // Generate colors for each job
                const colors = ['#8b5cf6', '#ec4899', '#14b8a6', '#f97316', '#06b6d4', '#84cc16', '#6366f1', '#f43f5e'];
                const jobIdArray = Array.from(jobIds).sort((a, b) => a - b);

                  return (
                    <>
                      <div style={{ width: '635px', position: 'absolute', left: '645px', top: '720px' }}>
                        <Card className="shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd' }}>
                      <CardHeader>
                        <CardTitle className="text-xl font-bold">{t('history:charts.avgProcessTime')}</CardTitle>
                      </CardHeader>
                      <CardContent>
                        <ResponsiveContainer width="100%" height={200}>
                          <BarChart data={transformedData}>
                            <CartesianGrid strokeDasharray="3 3" />
                            <XAxis
                              dataKey="date"
                              angle={-45}
                              textAnchor="end"
                              height={80}
                              style={{ fontSize: '12px' }}
                            />
                            <YAxis />
                            <Tooltip />
                            {jobIdArray.map((jobId, index) => (
                              <Bar
                                key={jobId}
                                dataKey={`Job ${jobId}`}
                                fill={colors[index % colors.length]}
                                name={`Job ${jobId}`}
                                stackId="a"
                                legendType="none"
                              >
                                {index === jobIdArray.length - 1 && (
                                  <LabelList dataKey="total" position="top" />
                                )}
                              </Bar>
                            ))}
                          </BarChart>
                        </ResponsiveContainer>
                      </CardContent>
                    </Card>
                      </div>

                      <div style={{ width: '635px', position: 'absolute', left: '645px', top: '960px' }}>
                        <Card className="shadow-lg border border-border" style={{ backgroundColor: '#fcfcfd' }}>
                        <CardHeader>
                          <CardTitle className="text-xl font-bold">{t('history:tables.processTimeDetails')}</CardTitle>
                        </CardHeader>
                      <CardContent>
                        <div className="overflow-x-auto" style={{ height: '400px', overflowY: 'auto' }}>
                          <table className="w-full border-collapse">
                            <thead>
                              <tr className="border-b border-gray-300">
                                <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.date')}</th>
                                <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.jobId')}</th>
                                <th className="text-left py-2 px-4 font-bold text-sm bg-gray-50">{t('history:columns.duration')}</th>
                              </tr>
                            </thead>
                            <tbody>
                              {filteredAvgProcessTimeData.map((item, index) => (
                                <tr
                                  key={index}
                                  className="border-b border-gray-200 hover:bg-gray-50 transition-colors"
                                >
                                  <td className="py-2 px-4">{item.date}</td>
                                  <td className="py-2 px-4">{item.job_id}</td>
                                  <td className="py-2 px-4">{item.duration_seconds ? Math.round(item.duration_seconds) : t('history:columns.notAvailable')}</td>
                                </tr>
                              ))}
                            </tbody>
                          </table>
                        </div>
                      </CardContent>
                      </Card>
                      </div>
                    </>
                  );
                })()}
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
