import { useState, useEffect, useRef, useCallback } from 'react';
import { useTranslation } from 'react-i18next';
import { jobsApi } from '../api/jobsApi';
import type { Order } from '../types/job.types';
import * as XLSX from 'xlsx';
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import {
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { Button } from '@/components/ui/button';
import { Alert, AlertDescription } from '@/components/ui/alert';
import { Loader2, AlertCircle, Download } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { FailureSummaryPanel } from './FailureSummaryPanel';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

interface DataReviewTableProps {
  jobId: number;
  onApprove: () => void;
  onReject: () => void;
}

const COLUMN_KEYS = [
  'orderNo',
  'customerId',
  'customerName',
  'sku',
  'qty',
  'reference',
  'valve',
  'deliveryAddress',
  'cpsd',
  'optionSku',
  'optionQty',
  'phone',
  'contact',
] as const;

const DEFAULT_WIDTHS: Record<string, number> = {
  orderNo: 100,
  customerId: 100,
  customerName: 150,
  sku: 100,
  qty: 80,
  reference: 120,
  valve: 100,
  deliveryAddress: 200,
  cpsd: 100,
  optionSku: 120,
  optionQty: 80,
  phone: 120,
  contact: 150,
};

export const DataReviewTable = ({ jobId, onApprove, onReject }: DataReviewTableProps) => {
  const { t } = useTranslation(['dataReview', 'common']);
  const [editedOrders, setEditedOrders] = useState<Order[]>([]);
  const [validationErrors, setValidationErrors] = useState<Map<string, string>>(new Map());
  const [isLoading, setIsLoading] = useState(true);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [columnWidths, setColumnWidths] = useState<Record<string, number>>(DEFAULT_WIDTHS);
  const [resizingColumn, setResizingColumn] = useState<string | null>(null);
  const resizeStartX = useRef<number>(0);
  const resizeStartWidth = useRef<number>(0);

  useEffect(() => {
    const fetchOrders = async () => {
      try {
        setIsLoading(true);
        const response = await jobsApi.getDataPreview(jobId);
        setEditedOrders(response.data);
      } catch (err) {
        setError(t('dataReview:status.loadFailed'));
        console.error('Error fetching data preview:', err);
      } finally {
        setIsLoading(false);
      }
    };

    fetchOrders();
  }, [jobId]);

  const validateCell = (_rowIndex: number, columnKey: string, value: any): string | null => {
    switch (columnKey) {
      case 'sku':
        if (!value || typeof value !== 'string') {
          return t('dataReview:validation.skuRequired');
        }
        if (value.length !== 13) {
          return t('dataReview:validation.skuLength');
        }
        break;

      case 'qty':
        if (value === '' || value === null || value === undefined) {
          return t('dataReview:validation.qtyRequired');
        }
        const qty = Number(value);
        if (isNaN(qty) || !Number.isInteger(qty) || qty <= 0) {
          return t('dataReview:validation.qtyPositive');
        }
        break;

      case 'optionQty':
        if (value !== '' && value !== null && value !== undefined) {
          const optQty = Number(value);
          if (isNaN(optQty) || optQty <= 0) {
            return t('dataReview:validation.optionQtyPositive');
          }
        }
        break;

      case 'orderNo':
        if (value === '' || value === null || value === undefined || value === 0) {
          return t('dataReview:validation.orderNoRequired');
        }
        const orderNo = Number(value);
        if (isNaN(orderNo) || !Number.isInteger(orderNo) || orderNo <= 0) {
          return t('dataReview:validation.orderNoPositive');
        }
        break;

      case 'valve':
        const validValves = ['Yes', 'no', 'Horizontal valve', 'Vertical valve', 'Rectangular valve'];
        if (value && !validValves.includes(value)) {
          return t('dataReview:validation.valveInvalid');
        }
        break;

      case 'cpsd':
        if (value && value !== '') {
          const dateRegex = /^\d{4}-\d{2}-\d{2}$/;
          if (!dateRegex.test(value)) {
            return t('dataReview:validation.cpsdFormat');
          }
          const date = new Date(value);
          if (isNaN(date.getTime())) {
            return t('dataReview:validation.invalidDate');
          }
        }
        break;
    }

    return null;
  };

  const handleCellChange = (rowIndex: number, columnKey: string, value: any) => {
    setEditedOrders(prev => {
      const updated = [...prev];
      const order = { ...updated[rowIndex] };
      
      switch (columnKey) {
        case 'orderNo':
          order.orderno = value === '' ? 0 : Number(value);
          break;
        case 'customerId':
          order.customerid = value === '' ? 0 : Number(value);
          break;
        case 'customerName':
          order.customer_name = value || '';
          break;
        case 'sku':
          order.sku = value || '';
          break;
        case 'qty':
          order.quantity = value === '' ? 0 : Number(value);
          break;
        case 'reference':
          order.reference_no = value || null;
          break;
        case 'valve':
          const validValveValues = ['Yes', 'no', 'Horizontal valve', 'Vertical valve', 'Rectangular valve'];
          order.valve = validValveValues.includes(value) ? value as typeof order.valve : "no";
          break;
        case 'deliveryAddress':
          order.delivery_address = value || null;
          break;
        case 'cpsd':
          order.cpsd = value || null;
          break;
        case 'optionSku':
          order.option_sku = value || null;
          break;
        case 'optionQty':
          order.option_qty = value === '' ? null : Number(value);
          break;
        case 'phone':
          order.telephone_number = value || null;
          break;
        case 'contact':
          order.contact_name = value || null;
          break;
      }
      
      updated[rowIndex] = order;
      return updated;
    });
  };

  const handleCellBlur = (rowIndex: number, columnKey: string, value: any) => {
    const error = validateCell(rowIndex, columnKey, value);
    const errorKey = `${rowIndex}_${columnKey}`;
    
    setValidationErrors(prev => {
      const updated = new Map(prev);
      if (error) {
        updated.set(errorKey, error);
      } else {
        updated.delete(errorKey);
      }
      return updated;
    });
  };

  const validateAllRows = (): boolean => {
    const errors = new Map<string, string>();
    
    editedOrders.forEach((order, rowIndex) => {
      COLUMN_KEYS.forEach(columnKey => {
        let value: any;
        switch (columnKey) {
          case 'orderNo':
            value = order.orderno;
            break;
          case 'customerId':
            value = order.customerid;
            break;
          case 'customerName':
            value = order.customer_name;
            break;
          case 'sku':
            value = order.sku;
            break;
          case 'qty':
            value = order.quantity;
            break;
          case 'reference':
            value = order.reference_no;
            break;
          case 'valve':
            value = order.valve;
            break;
          case 'deliveryAddress':
            value = order.delivery_address;
            break;
          case 'cpsd':
            value = order.cpsd;
            break;
          case 'optionSku':
            value = order.option_sku;
            break;
          case 'optionQty':
            value = order.option_qty;
            break;
          case 'phone':
            value = order.telephone_number;
            break;
          case 'contact':
            value = order.contact_name;
            break;
        }
        
        const error = validateCell(rowIndex, columnKey, value);
        if (error) {
          errors.set(`${rowIndex}_${columnKey}`, error);
        }
      });
    });
    
    setValidationErrors(errors);
    return errors.size === 0;
  };

  const handleResizeStart = useCallback((columnKey: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setResizingColumn(columnKey);
    resizeStartX.current = e.clientX;
    resizeStartWidth.current = columnWidths[columnKey];
    
    const handleMouseMove = (e: MouseEvent) => {
      const diff = e.clientX - resizeStartX.current;
      const newWidth = Math.max(50, resizeStartWidth.current + diff);
      setColumnWidths(prev => ({ ...prev, [columnKey]: newWidth }));
    };

    const handleMouseUp = () => {
      setResizingColumn(null);
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
  }, [columnWidths]);

  const handleApprove = async () => {
    // Validate rows for UI feedback, but don't block approval
    // Backend validation will separate valid/invalid orders
    validateAllRows();

    if (validationErrors.size > 0) {
      console.warn(`Proceeding with ${validationErrors.size} validation errors. Invalid orders will be logged to failed_orders.csv`);
    }

    try {
      setIsSubmitting(true);
      setError(null);
      
      const ordersToSend = editedOrders.map(order => ({
        orderno: order.orderno,
        customerid: order.customerid,
        customer_name: order.customer_name,
        sku: order.sku,
        quantity: order.quantity,
        reference_no: order.reference_no,
        valve: order.valve,
        delivery_address: order.delivery_address,
        cpsd: order.cpsd,
        entry_id: order.entry_id,
        option_sku: order.option_sku,
        option_qty: order.option_qty,
        telephone_number: order.telephone_number,
        contact_name: order.contact_name,
      }));
      
      // Cast to any because backend expects "Yes" while Order type expects "yes"
      await jobsApi.approveData(jobId, true, ordersToSend as any);
      await onApprove();
    } catch (err) {
      setError(t('common:status.failed'));
      console.error('Error approving data:', err);
      setIsSubmitting(false);
    }
  };

  const handleReject = async () => {
    try {
      setIsSubmitting(true);
      await jobsApi.approveData(jobId, false);
      onReject();
    } catch (err) {
      setError(t('common:status.failed'));
      console.error('Error rejecting data:', err);
      setIsSubmitting(false);
    }
  };

  const handleExportToExcel = () => {
    if (editedOrders.length === 0) {
      setError(t('dataReview:status.noData'));
      return;
    }

    try {
      const worksheetData = editedOrders.map(order => ({
        'Order No': order.orderno,
        'Customer ID': order.customerid,
        'Customer Name': order.customer_name,
        'SKU': order.sku,
        'Qty': order.quantity,
        'Reference': order.reference_no || '-',
        'Valve': order.valve,
        'Delivery Address': order.delivery_address || '-',
        'CPSD': order.cpsd || '-',
        'Option SKU': order.option_sku || '-',
        'Option Qty': order.option_qty || '-',
        'Phone': order.telephone_number || '-',
        'Contact': order.contact_name || '-',
      }));

      const worksheet = XLSX.utils.json_to_sheet(worksheetData);
      const workbook = XLSX.utils.book_new();
      XLSX.utils.book_append_sheet(workbook, worksheet, 'Extracted Data');

      const fileName = `extracted_data_job_${jobId}_${new Date().toISOString().split('T')[0]}.xlsx`;
      XLSX.writeFile(workbook, fileName);
    } catch (err) {
      setError(t('dataReview:status.exportFailed'));
      console.error('Error exporting to Excel:', err);
    }
  };

  return (
    <Dialog open modal={false} onOpenChange={() => {}}>
      <DialogContent className="max-w-[95vw] max-h-[85vh] flex flex-col shadow-2xl [&>button]:hidden p-4 gap-2 top-[50%]" style={{ backgroundColor: '#f5f5f5', overflow: 'hidden' }}>
        <DialogHeader className="space-y-0 pb-2">
          <div className="flex justify-between items-center">
            <DialogTitle className="text-lg">{t('dataReview:dialog.title')}</DialogTitle>
            <Button
              onClick={handleExportToExcel}
              disabled={isLoading || editedOrders.length === 0}
              variant="outline"
              size="sm"
              className="gap-2"
              style={{ backgroundColor: '#f5f5f5' }}
            >
              <Download className="h-4 w-4" />
              {t('common:buttons.exportExcel')}
            </Button>
          </div>
        </DialogHeader>

        <div className="flex-1 min-h-0 mb-4">
          {isLoading ? (
            <div className="flex justify-center items-center h-64">
              <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
              <span className="ml-2 text-muted-foreground">{t('dataReview:status.loading')}</span>
            </div>
          ) : error ? (
            <Alert variant="destructive" className="mb-4">
              <AlertCircle className="h-4 w-4" />
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          ) : (
            <>
              {validationErrors.size > 0 && (
                <Alert variant="destructive" className="mb-4">
                  <AlertCircle className="h-4 w-4" />
                  <AlertDescription>
                    {t('dataReview:validation.errorsDetected', { count: validationErrors.size })}
                  </AlertDescription>
                </Alert>
              )}
              {/* Failure Summary Panel - shows analysis of failed orders */}
              <div className="mb-4">
                <FailureSummaryPanel jobId={jobId} compact={true} />
              </div>
            <div className="h-[40vh] rounded-md border overflow-auto" style={{ maxWidth: '100%' }}>
              <table className="caption-bottom text-sm" style={{ tableLayout: 'fixed', minWidth: 'max-content' }}>
                <TableHeader>
                  <TableRow>
                    {COLUMN_KEYS.map((key, index) => {
                      const isCentered = ['orderNo', 'customerId', 'qty', 'valve', 'cpsd', 'optionQty', 'phone'].includes(key);
                      return (
                      <TableHead
                        key={key}
                        style={{ 
                          width: `${columnWidths[key]}px`,
                          minWidth: `${columnWidths[key]}px`,
                          maxWidth: `${columnWidths[key]}px`,
                          position: 'relative',
                          backgroundColor: 'white',
                          boxShadow: 'inset 1px 1px 2px rgba(0,0,0,0.1), inset -1px -1px 1px rgba(255,255,255,0.8)',
                        }}
                        className={`font-bold text-black ${isCentered ? 'text-center' : ''}`}
                      >
                        <div className={isCentered ? '' : 'pr-3'}>
                          {t(`dataReview:columns.${key}`)}
                        </div>
                        {index < COLUMN_KEYS.length - 1 && (
                          <div
                            onMouseDown={(e) => {
                              e.preventDefault();
                              e.stopPropagation();
                              const columnKey = COLUMN_KEYS[index];
                              console.log('Resizing column:', columnKey, 'at index:', index);
                              handleResizeStart(columnKey, e);
                            }}
                            className={`absolute right-[-2px] top-0 h-full w-1 cursor-col-resize border-r-2 border-gray-400 hover:border-blue-500 hover:w-1.5 transition-all ${
                              resizingColumn === COLUMN_KEYS[index] ? 'border-blue-600 w-2 bg-blue-100' : ''
                            }`}
                            style={{ 
                              userSelect: 'none',
                              zIndex: 10,
                              pointerEvents: 'auto',
                            }}
                            data-column={COLUMN_KEYS[index]}
                            title={`Drag to resize ${COLUMN_KEYS[index] === 'sku' ? 'SKU' : COLUMN_KEYS[index] === 'qty' ? 'Qty' : 'column'}`}
                          />
                        )}
                      </TableHead>
                      );
                    })}
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {editedOrders.map((order, idx) => {
                    const cellStyle = { backgroundColor: 'white', boxShadow: 'inset 1px 1px 2px rgba(0,0,0,0.1), inset -1px -1px 1px rgba(255,255,255,0.8)' };
                    const getError = (key: string) => validationErrors.get(`${idx}_${key}`);
                    
                    return (
                    <TableRow key={idx}>
                        <TableCell style={{ width: `${columnWidths.orderNo}px`, ...cellStyle }} className="text-center p-1">
                          <Input
                            type="number"
                            value={order.orderno || ''}
                            onChange={(e) => handleCellChange(idx, 'orderNo', e.target.value)}
                            onBlur={(e) => handleCellBlur(idx, 'orderNo', e.target.value)}
                            className="text-center h-8 text-sm border-0 focus-visible:ring-1"
                          />
                          {getError('orderNo') && (
                            <div className="text-xs text-red-600 mt-0.5">{getError('orderNo')}</div>
                          )}
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.customerId}px`, ...cellStyle }} className="text-center p-1">
                          <Input
                            type="number"
                            value={order.customerid || ''}
                            onChange={(e) => handleCellChange(idx, 'customerId', e.target.value)}
                            onBlur={(e) => handleCellBlur(idx, 'customerId', e.target.value)}
                            className="text-center h-8 text-sm border-0 focus-visible:ring-1"
                          />
                          {getError('customerId') && (
                            <div className="text-xs text-red-600 mt-0.5">{getError('customerId')}</div>
                          )}
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.customerName}px`, ...cellStyle }} className="p-1">
                          <Input
                            type="text"
                            value={order.customer_name || ''}
                            onChange={(e) => handleCellChange(idx, 'customerName', e.target.value)}
                            className="h-8 text-sm border-0 focus-visible:ring-1"
                          />
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.sku}px`, ...cellStyle }} className="p-1">
                          <Input
                            type="text"
                            value={order.sku || ''}
                            onChange={(e) => handleCellChange(idx, 'sku', e.target.value)}
                            onBlur={(e) => handleCellBlur(idx, 'sku', e.target.value)}
                            className="h-8 text-sm border-0 focus-visible:ring-1"
                            maxLength={13}
                          />
                          {getError('sku') && (
                            <div className="text-xs text-red-600 mt-0.5">{getError('sku')}</div>
                          )}
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.qty}px`, ...cellStyle }} className="text-center p-1">
                          <Input
                            type="number"
                            value={order.quantity || ''}
                            onChange={(e) => handleCellChange(idx, 'qty', e.target.value)}
                            onBlur={(e) => handleCellBlur(idx, 'qty', e.target.value)}
                            className="text-center h-8 text-sm border-0 focus-visible:ring-1"
                            min="1"
                          />
                          {getError('qty') && (
                            <div className="text-xs text-red-600 mt-0.5">{getError('qty')}</div>
                          )}
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.reference}px`, ...cellStyle }} className="p-1">
                          <Input
                            type="text"
                            value={order.reference_no || ''}
                            onChange={(e) => handleCellChange(idx, 'reference', e.target.value)}
                            className="h-8 text-sm border-0 focus-visible:ring-1"
                          />
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.valve}px`, ...cellStyle }} className="text-center p-1">
                          <Select
                            value={order.valve || 'no'}
                            onValueChange={(value) => {
                              handleCellChange(idx, 'valve', value);
                              handleCellBlur(idx, 'valve', value);
                            }}
                          >
                            <SelectTrigger className="h-8 text-sm border-0 focus:ring-1">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent>
                              <SelectItem value="no">no</SelectItem>
                              <SelectItem value="Yes">Yes</SelectItem>
                              <SelectItem value="Horizontal valve">Horizontal valve</SelectItem>
                              <SelectItem value="Vertical valve">Vertical valve</SelectItem>
                              <SelectItem value="Rectangular valve">Rectangular valve</SelectItem>
                            </SelectContent>
                          </Select>
                          {getError('valve') && (
                            <div className="text-xs text-red-600 mt-0.5">{getError('valve')}</div>
                          )}
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.deliveryAddress}px`, ...cellStyle }} className="p-1">
                          <Input
                            type="text"
                            value={order.delivery_address || ''}
                            onChange={(e) => handleCellChange(idx, 'deliveryAddress', e.target.value)}
                            className="h-8 text-sm border-0 focus-visible:ring-1"
                          />
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.cpsd}px`, ...cellStyle }} className="text-center p-1">
                          <Input
                            type="date"
                            value={order.cpsd || ''}
                            onChange={(e) => handleCellChange(idx, 'cpsd', e.target.value)}
                            onBlur={(e) => handleCellBlur(idx, 'cpsd', e.target.value)}
                            className="text-center h-8 text-sm border-0 focus-visible:ring-1"
                          />
                          {getError('cpsd') && (
                            <div className="text-xs text-red-600 mt-0.5">{getError('cpsd')}</div>
                          )}
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.optionSku}px`, ...cellStyle }} className="p-1">
                          <Input
                            type="text"
                            value={order.option_sku || ''}
                            onChange={(e) => handleCellChange(idx, 'optionSku', e.target.value)}
                            className="h-8 text-sm border-0 focus-visible:ring-1"
                          />
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.optionQty}px`, ...cellStyle }} className="text-center p-1">
                          <Input
                            type="number"
                            step="0.01"
                            value={order.option_qty ?? ''}
                            onChange={(e) => handleCellChange(idx, 'optionQty', e.target.value)}
                            onBlur={(e) => handleCellBlur(idx, 'optionQty', e.target.value)}
                            className="text-center h-8 text-sm border-0 focus-visible:ring-1"
                          />
                          {getError('optionQty') && (
                            <div className="text-xs text-red-600 mt-0.5">{getError('optionQty')}</div>
                          )}
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.phone}px`, ...cellStyle }} className="text-center p-1">
                          <Input
                            type="text"
                            value={order.telephone_number || ''}
                            onChange={(e) => handleCellChange(idx, 'phone', e.target.value)}
                            className="text-center h-8 text-sm border-0 focus-visible:ring-1"
                          />
                        </TableCell>
                        
                        <TableCell style={{ width: `${columnWidths.contact}px`, ...cellStyle }} className="p-1">
                          <Input
                            type="text"
                            value={order.contact_name || ''}
                            onChange={(e) => handleCellChange(idx, 'contact', e.target.value)}
                            className="h-8 text-sm border-0 focus-visible:ring-1"
                          />
                        </TableCell>
                    </TableRow>
                    );
                  })}
                </TableBody>
              </table>
            </div>
            </>
          )}
        </div>

        <DialogFooter className="pt-4 pb-4">
          <div className="flex gap-8 justify-center w-full">
            <Button
              onClick={handleApprove}
              disabled={isSubmitting || isLoading}
              variant="outline"
              style={{
                height: '64px',
                minHeight: '64px',
                width: '288px',
                backgroundColor: 'white',
                color: '#4CAF50',
                fontWeight: 'bold',
                fontSize: '1.875rem',
                marginRight: '16px',
                border: '2px solid #4CAF50',
                borderRadius: '9px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
                transition: 'all 0.2s ease',
              }}
              className="hover:bg-green-50 hover:shadow-md"
            >
              {isSubmitting ? t('common:status.approving') : t('common:buttons.approve')}
            </Button>
            <Button
              onClick={handleReject}
              disabled={isSubmitting || isLoading}
              variant="outline"
              style={{
                height: '64px',
                minHeight: '64px',
                width: '288px',
                backgroundColor: 'white',
                color: '#D32F2F',
                fontWeight: 'bold',
                fontSize: '1.875rem',
                marginLeft: '16px',
                border: '2px solid #D32F2F',
                borderRadius: '9px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
                transition: 'all 0.2s ease',
              }}
              className="hover:bg-red-50 hover:shadow-md"
            >
              {t('common:buttons.reject')}
            </Button>
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
};

