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
    phases: {
      list: (eventId: string, dayId: string) => `/events/${eventId}/event-days/${dayId}/phases`,
      byId: (eventId: string, dayId: string, phaseId: string) =>
        `/events/${eventId}/event-days/${dayId}/phases/${phaseId}`,
    },
  },
  predictions: {
    get: (eventId: string) => `/events/${eventId}/predictions`,
  },
  recommendations: {
    list: (eventId: string) =>
      `/events/${eventId}/recommendations`,
  },
  motorConfig: {
    recommendationConfig: '/recommendation-config',
    stage4Config: '/stage4-config',
  },
  operationalEvents: {
    list: (eventDayId: string) => `/operational-events/by-event-day/${eventDayId}`,
    byId: (id: string) => `/operational-events/${id}`,
    create: `/operational-events/`,
  },
  products: {
    parking: (eventId: string) =>
      `/events/${eventId}/products/parking`,
    gastronomy: (eventId: string) =>
      `/events/${eventId}/products/gastronomy`,
    transport: (eventId: string) =>
      `/events/${eventId}/products/transport`,
    bathroom: (eventId: string) =>
      `/events/${eventId}/products/bathroom`,
    rest: (eventId: string) =>
      `/events/${eventId}/products/rest`,
    health: (eventId: string) =>
      `/events/${eventId}/products/health`,
    hydration: (eventId: string) =>
      `/events/${eventId}/products/hydration`,
  },
};
