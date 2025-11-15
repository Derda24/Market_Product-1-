import { useLanguage } from '../contexts/LanguageContext';
import { Globe } from 'lucide-react';

const LANGUAGE_OPTIONS = [
  { code: 'en', flag: '🇬🇧', short: 'EN', labelKey: 'language.english' },
  { code: 'es', flag: '🇪🇸', short: 'ES', labelKey: 'language.spanish' },
  { code: 'it', flag: '🇮🇹', short: 'IT', labelKey: 'language.italian' },
  { code: 'fr', flag: '🇫🇷', short: 'FR', labelKey: 'language.french' },
  { code: 'de', flag: '🇩🇪', short: 'DE', labelKey: 'language.german' },
];

export const LanguageSwitcher: React.FC = () => {
  const { setLocale, locale, t } = useLanguage();

  const handleLanguageChange = (newLocale: string) => {
    setLocale(newLocale);
  };

  const activeLanguage =
    LANGUAGE_OPTIONS.find(option => option.code === locale) || LANGUAGE_OPTIONS[0];

  return (
    <div className="relative group">
      <button className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors">
        <Globe className="w-4 h-4" />
        <span className="text-sm font-medium">
          {activeLanguage.short}
        </span>
      </button>
      
      <div className="absolute right-0 mt-2 w-40 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
        <div className="py-1">
          {LANGUAGE_OPTIONS.map(option => (
            <button
              key={option.code}
              onClick={() => handleLanguageChange(option.code)}
              className={`flex items-center gap-2 w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors ${
                locale === option.code ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
              }`}
            >
              <span>{option.flag}</span>
              {t(option.labelKey)}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
};
