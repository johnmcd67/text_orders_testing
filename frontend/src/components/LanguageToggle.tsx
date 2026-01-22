import { useTranslation } from 'react-i18next';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';

const languages = [
  { code: 'en', label: 'EN', fullName: 'English' },
  { code: 'es', label: 'ES', fullName: 'Español' },
];

export const LanguageToggle = () => {
  const { i18n } = useTranslation();

  const handleLanguageChange = (languageCode: string) => {
    i18n.changeLanguage(languageCode);
  };

  const currentLang = languages.find((lang) => lang.code === i18n.language) || languages[0];

  return (
    <Select value={i18n.language} onValueChange={handleLanguageChange}>
      <SelectTrigger
        className="w-[70px] h-[36px] bg-white border-2 border-white rounded-md text-blue-600 font-semibold hover:bg-blue-50 transition-all"
        style={{ minHeight: '36px' }}
      >
        <SelectValue>
          <span>{currentLang.label}</span>
        </SelectValue>
      </SelectTrigger>
      <SelectContent className="z-[100]">
        {languages.map((lang) => (
          <SelectItem key={lang.code} value={lang.code}>
            <span>{lang.fullName}</span>
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  );
};
