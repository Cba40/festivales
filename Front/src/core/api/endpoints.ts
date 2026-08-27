export const endpoints = {
  auth: {
    login: '/auth/login',
  },
  events: {
    get: (id: string) => `/events/${id}`,
    update: (id: string) => `/events/${id}`,
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
  serviceConfigs: {
    list: () => '/service-configs',
    create: () => '/service-configs',
    update: (id: string) => `/service-configs/${id}`,
    delete: (id: string) => `/service-configs/${id}`,
  },
  contextEngine: {
    zoneTypes: () => '/context-engine/zone-types',
    zoneSubtypes: () => '/context-engine/zone-subtypes',
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
    exit: (eventId: string) =>
      `/events/${eventId}/products/exit`,
    bathroom: (eventId: string) =>
      `/events/${eventId}/products/bathroom`,
    rest: (eventId: string) =>
      `/events/${eventId}/products/rest`,
    health: (eventId: string) =>
      `/events/${eventId}/products/health`,
    hydration: (eventId: string) =>
      `/events/${eventId}/products/hydration`,
  },
  exitAdmin: {
    destinations: {
      list: (eventId: string) => `/events/${eventId}/exit-destinations`,
      create: (eventId: string) => `/events/${eventId}/exit-destinations`,
      update: (eventId: string, id: string) => `/events/${eventId}/exit-destinations/${id}`,
      delete: (eventId: string, id: string) => `/events/${eventId}/exit-destinations/${id}`,
    },
    zoneDestinations: {
      get: (eventId: string, zoneId: string) =>
        `/events/${eventId}/zones/${zoneId}/exit-destinations`,
      update: (eventId: string, zoneId: string) =>
        `/events/${eventId}/zones/${zoneId}/exit-destinations`,
    },
  },
  transportAdmin: {
    lines: {
      list: (eventId: string) => `/events/${eventId}/transport-lines`,
      create: (eventId: string) => `/events/${eventId}/transport-lines`,
      update: (eventId: string, id: string) => `/events/${eventId}/transport-lines/${id}`,
      delete: (eventId: string, id: string) => `/events/${eventId}/transport-lines/${id}`,
    },
    stops: {
      list: (eventId: string, lineId: string) =>
        `/events/${eventId}/transport-lines/${lineId}/stops`,
      update: (eventId: string, lineId: string) =>
        `/events/${eventId}/transport-lines/${lineId}/stops`,
    },
    schedules: {
      list: (eventId: string, lineId: string) =>
        `/events/${eventId}/transport-lines/${lineId}/schedules`,
      update: (eventId: string, lineId: string) =>
        `/events/${eventId}/transport-lines/${lineId}/schedules`,
    },
    importCsv: (eventId: string) => `/events/${eventId}/transport/import-csv`,
  },
};
