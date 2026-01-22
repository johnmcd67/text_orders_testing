import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';

// English translations
import commonEN from '../locales/en/common.json';
import landingEN from '../locales/en/landing.json';
import dashboardEN from '../locales/en/dashboard.json';
import dataReviewEN from '../locales/en/dataReview.json';
import historyEN from '../locales/en/history.json';
import promptsEN from '../locales/en/prompts.json';
import failureSummaryEN from '../locales/en/failureSummary.json';
import loginEN from '../locales/en/login.json';
import errorsEN from '../locales/en/errors.json';

// Spanish translations
import commonES from '../locales/es/common.json';
import landingES from '../locales/es/landing.json';
import dashboardES from '../locales/es/dashboard.json';
import dataReviewES from '../locales/es/dataReview.json';
import historyES from '../locales/es/history.json';
import promptsES from '../locales/es/prompts.json';
import failureSummaryES from '../locales/es/failureSummary.json';
import loginES from '../locales/es/login.json';
import errorsES from '../locales/es/errors.json';

const resources = {
  en: {
    common: commonEN,
    landing: landingEN,
    dashboard: dashboardEN,
    dataReview: dataReviewEN,
    history: historyEN,
    prompts: promptsEN,
    failureSummary: failureSummaryEN,
    login: loginEN,
    errors: errorsEN,
  },
  es: {
    common: commonES,
    landing: landingES,
    dashboard: dashboardES,
    dataReview: dataReviewES,
    history: historyES,
    prompts: promptsES,
    failureSummary: failureSummaryES,
    login: loginES,
    errors: errorsES,
  },
};

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources,
    fallbackLng: 'en',
    defaultNS: 'common',
    ns: [
      'common',
      'landing',
      'dashboard',
      'dataReview',
      'history',
      'prompts',
      'failureSummary',
      'login',
      'errors',
    ],
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
      lookupLocalStorage: 'i18nextLng',
    },
    interpolation: {
      escapeValue: false,
    },
  });

export default i18n;
