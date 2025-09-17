'use client';

import React, { createContext, useContext, useState, useEffect } from 'react';

interface LanguageContextType {
  locale: string;
  setLocale: (locale: string) => void;
  t: (key: string) => string;
  loading: boolean;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const useLanguage = () => {
  const context = useContext(LanguageContext);
  if (context === undefined) {
    throw new Error('useLanguage must be used within a LanguageProvider');
  }
  return context;
};

interface Translations {
  [key: string]: any;
}

export const LanguageProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [locale, setLocale] = useState('en');
  const [translations, setTranslations] = useState<Translations>({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // load persisted locale if present
    if (typeof window !== 'undefined') {
      const saved = localStorage.getItem('locale');
      if (saved) {
        setLocale(saved);
      }
    }
    const loadTranslations = async () => {
      try {
        const response = await fetch(`/locales/${locale}/common.json`);
        const data = await response.json();
        setTranslations(data);
        setLoading(false);
      } catch (error) {
        console.error('Error loading translations:', error);
        setLoading(false);
      }
    };

    loadTranslations();
  }, [locale]);

  const t = (key: string): string => {
    const keys = key.split('.');
    let value: any = translations;
    
    for (const k of keys) {
      if (value && typeof value === 'object' && k in value) {
        value = value[k];
      } else {
        return key; // Return key if translation not found
      }
    }
    
    return typeof value === 'string' ? value : key;
  };

  const changeLocale = (newLocale: string) => {
    setLocale(newLocale);
    if (typeof window !== 'undefined') localStorage.setItem('locale', newLocale);
    setLoading(true);
  };

  return (
    <LanguageContext.Provider value={{ locale, setLocale: changeLocale, t, loading }}>
      {children}
    </LanguageContext.Provider>
  );
};
