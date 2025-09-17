import { useLanguage } from '../contexts/LanguageContext';
import { Globe } from 'lucide-react';

export const LanguageSwitcher: React.FC = () => {
  const { setLocale, locale } = useLanguage();

  const handleLanguageChange = (newLocale: string) => {
    setLocale(newLocale);
  };

  return (
    <div className="relative group">
      <button className="flex items-center space-x-2 px-3 py-2 rounded-lg bg-white/10 hover:bg-white/20 transition-colors">
        <Globe className="w-4 h-4" />
        <span className="text-sm font-medium">
          {locale === 'es' ? 'ES' : 'EN'}
        </span>
      </button>
      
      <div className="absolute right-0 mt-2 w-32 bg-white rounded-lg shadow-lg border border-gray-200 opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-200 z-50">
        <div className="py-1">
          <button
            onClick={() => handleLanguageChange('es')}
            className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors ${
              locale === 'es' ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
            }`}
          >
            🇪🇸 Español
          </button>
          <button
            onClick={() => handleLanguageChange('en')}
            className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-100 transition-colors ${
              locale === 'en' ? 'bg-blue-50 text-blue-600' : 'text-gray-700'
            }`}
          >
            🇬🇧 English
          </button>
        </div>
      </div>
    </div>
  );
};
