import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useTranslation } from 'react-i18next';
import { Button } from '@/components/ui/button';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { ArrowLeft, Download } from 'lucide-react';
import { promptsApi } from '@/api/promptsApi';
import { LanguageToggle } from './LanguageToggle';

const PROMPTS = [
  { filename: 'customer_id.txt', translationKey: 'customerId' },
  { filename: 'sku_extraction.txt', translationKey: 'sku' },
  { filename: 'delivery_address.txt', translationKey: 'deliveryAddress' },
  { filename: 'reference_no.txt', translationKey: 'referenceNo' },
  { filename: 'valve_detection.txt', translationKey: 'valve' },
  { filename: 'cpsd_extraction.txt', translationKey: 'cpsd' },
  { filename: 'options_extraction.txt', translationKey: 'options' },
];

export const ViewPrompts = () => {
  const navigate = useNavigate();
  const { t } = useTranslation(['prompts', 'common']);
  const [selectedPrompt, setSelectedPrompt] = useState<{ filename: string; content: string } | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handlePromptClick = async (filename: string) => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await promptsApi.getPrompt(filename);
      setSelectedPrompt(data);
    } catch (err: any) {
      setError(err.response?.data?.detail || t('prompts:errors.loadFailed'));
    } finally {
      setIsLoading(false);
    }
  };

  const handleExportPrompt = () => {
    if (!selectedPrompt) return;

    const blob = new Blob([selectedPrompt.content], { type: 'text/plain' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = selectedPrompt.filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    window.URL.revokeObjectURL(url);
  };

  return (
    <div className="min-h-screen flex flex-col" style={{ backgroundColor: '#f5f5f5' }}>
      {/* Blue Header Bar */}
      <header
        style={{
          backgroundColor: '#2196F3',
          padding: '24px 32px',
          boxShadow: '0 2px 4px rgba(0, 0, 0, 0.1)',
          position: 'relative',
          zIndex: 60,
        }}
      >
        <div className="container mx-auto max-w-7xl flex items-center justify-center relative">
          <div style={{ position: 'absolute', left: 0 }}>
            <LanguageToggle />
          </div>
          <h1
            style={{
              color: 'white',
              fontSize: '1.75rem',
              fontWeight: '500',
              margin: 0,
              letterSpacing: '-0.01em',
              textAlign: 'center',
            }}
          >
            {t('prompts:title')}
          </h1>
          <Button
            onClick={() => navigate('/')}
            variant="outline"
            style={{
              position: 'absolute',
              right: 0,
              height: '40px',
              minHeight: '40px',
              backgroundColor: 'white',
              color: '#1976D2',
              fontWeight: '600',
              border: '2px solid white',
              borderRadius: '6px',
              transition: 'all 0.2s ease',
            }}
            className="hover:bg-blue-50"
          >
            <ArrowLeft className="mr-2 h-4 w-4" />
            {t('common:buttons.backToHome')}
          </Button>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col items-center" style={{ padding: '48px 24px' }}>
        {/* Prompt Buttons - Vertical Stack */}
        <div className="flex flex-col items-center" style={{ gap: '16px' }}>
          {PROMPTS.map((prompt) => (
            <Button
              key={prompt.filename}
              onClick={() => handlePromptClick(prompt.filename)}
              disabled={isLoading}
              style={{
                height: '56px',
                minHeight: '56px',
                width: '220px',
                backgroundColor: 'white',
                color: '#1976D2',
                fontWeight: '600',
                fontSize: '1.125rem',
                border: '2px solid #1976D2',
                borderRadius: '9px',
                boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
                transition: 'all 0.2s ease',
              }}
              className="hover:bg-blue-50 hover:shadow-md disabled:opacity-50"
            >
              {t(`prompts:buttons.${prompt.translationKey}`)}
            </Button>
          ))}
        </div>
      </main>

      {/* Prompt Dialog */}
      <Dialog open={selectedPrompt !== null} onOpenChange={() => setSelectedPrompt(null)}>
        <DialogContent className="max-w-4xl max-h-[85vh] flex flex-col top-[55%] z-[100]">
          <DialogHeader className="pb-4" style={{ paddingLeft: '3rem' }}>
            <div className="flex items-center justify-between">
              <DialogTitle style={{ marginLeft: '0.5rem' }}>{selectedPrompt?.filename || t('prompts:dialog.title')}</DialogTitle>
              <Button
                onClick={handleExportPrompt}
                variant="outline"
                style={{
                  height: '36px',
                  minHeight: '36px',
                  backgroundColor: 'white',
                  color: '#1976D2',
                  fontWeight: '600',
                  border: '2px solid #1976D2',
                  borderRadius: '6px',
                  transition: 'all 0.2s ease',
                }}
                className="hover:bg-blue-50"
              >
                <Download className="mr-2 h-4 w-4" />
                {t('common:buttons.exportTxt')}
              </Button>
            </div>
          </DialogHeader>
          <ScrollArea className="h-[65vh] pr-4">
            <pre className="whitespace-pre-wrap font-mono text-sm bg-muted p-4 rounded-md">
              {selectedPrompt?.content || ''}
            </pre>
          </ScrollArea>
        </DialogContent>
      </Dialog>

      {/* Error Display */}
      {error && (
        <div className="fixed bottom-8 left-1/2 transform -translate-x-1/2">
          <div style={{
            backgroundColor: '#fef2f2',
            border: '2px solid #ef4444',
            borderRadius: '9px',
            padding: '16px 24px',
            boxShadow: '0 1px 3px rgba(0, 0, 0, 0.08)',
          }}>
            <p style={{ color: '#dc2626', fontWeight: '600' }}>{error}</p>
          </div>
        </div>
      )}
    </div>
  );
};

