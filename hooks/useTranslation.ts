import { useLanguage } from '@/contexts/LanguageContext';

export const useTranslation = () => {
  const { locale, setLocale, t, loading } = useLanguage();

  return {
    t,
    changeLanguage: setLocale,
    locale,
    loading
  };
};
