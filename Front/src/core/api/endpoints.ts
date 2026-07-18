export const endpoints = {
  auth: {
    login: '/auth/login',
  },
  events: {
    get: (id: string) => `/events/${id}`,
  },
  zones: {
    list: (eventId: string) => `/events/${eventId}/zones`,
    create: (eventId: string) => `/events/${eventId}/zones`,
    update: (eventId: string, id: string) => `/events/${eventId}/zones/${id}`,
    updateConfig: (eventId: string, id: string) => `/events/${eventId}/zones/${id}/config`,
    delete: (eventId: string, id: string) => `/events/${eventId}/zones/${id}`,
  },
  incidents: {
    list: (eventId: string) => `/events/${eventId}/incidents`,
    create: (eventId: string) => `/events/${eventId}/incidents`,
  },
  eventDays: {
    list: (eventId: string) => `/events/${eventId}/event-days`,
    today: (eventId: string) => `/events/${eventId}/event-days/today`,
    byId: (eventId: string, id: string) => `/events/${eventId}/event-days/${id}`,
  },
  recommendations: {
    list: (eventId: string) =>
      `/events/${eventId}/recommendations`,
  },
};
