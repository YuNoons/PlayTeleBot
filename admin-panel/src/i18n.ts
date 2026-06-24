const translations: Record<string, Record<string, string>> = {
  en: {
    dashboard: "Dashboard",
    users: "Users & Economy",
    store: "Store & Items",
    rooms: "Active Rooms",
    admins: "Administrators",
    reports: "User Reports",
    broadcast: "Broadcasting",
    settings: "Settings",
    loading: "Loading...",
    refresh: "Refresh Data",
    search: "Search",
    save: "Save Changes",
    cancel: "Cancel",
  },
  ru: {
    dashboard: "Дашборд",
    users: "Игроки и Экономика",
    store: "Магазин и Предметы",
    rooms: "Активные Комнаты",
    admins: "Администраторы",
    reports: "Жалобы",
    broadcast: "Рассылка",
    settings: "Настройки",
    loading: "Загрузка...",
    refresh: "Обновить данные",
    search: "Поиск",
    save: "Сохранить",
    cancel: "Отмена",
  }
};

export function t(key: string): string {
  const lang = localStorage.getItem('app_language') || 'en';
  return translations[lang]?.[key] || translations['en'][key] || key;
}
