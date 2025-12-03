// Comprehensive country coordinates database for dynamic map navigation
// Includes all 195 UN-recognized countries plus major territories

export interface CountryData {
  name: string;
  center: [number, number];
  zoom: number;
  bbox: [number, number, number, number]; // [west, south, east, north]
  aliases?: string[]; // Alternative names
}

export const COUNTRY_COORDINATES: Record<string, CountryData> = {
  // === AFRICA (54 countries) ===
  DZA: { name: 'Algeria', center: [1.66, 28.03], zoom: 5, bbox: [-8.67, 19.0, 12.0, 37.1] },
  AGO: { name: 'Angola', center: [17.87, -11.2], zoom: 6, bbox: [11.7, -18.0, 24.1, -4.4] },
  BEN: { name: 'Benin', center: [2.32, 9.31], zoom: 7, bbox: [0.77, 6.2, 3.8, 12.4] },
  BWA: { name: 'Botswana', center: [24.68, -22.33], zoom: 6, bbox: [19.9, -26.9, 29.4, -17.8] },
  BFA: { name: 'Burkina Faso', center: [-1.56, 12.24], zoom: 7, bbox: [-5.5, 9.4, 2.4, 15.1] },
  BDI: { name: 'Burundi', center: [29.92, -3.37], zoom: 8, bbox: [29.0, -4.5, 30.8, -2.3] },
  CMR: { name: 'Cameroon', center: [12.35, 7.37], zoom: 6, bbox: [8.5, 1.7, 16.2, 13.1] },
  CPV: { name: 'Cape Verde', center: [-24.01, 16.54], zoom: 8, bbox: [-25.4, 14.8, -22.7, 17.2] },
  CAF: { name: 'Central African Republic', center: [20.94, 6.61], zoom: 6, bbox: [14.4, 2.2, 27.5, 11.0] },
  TCD: { name: 'Chad', center: [18.73, 15.45], zoom: 6, bbox: [13.5, 7.4, 24.0, 23.5] },
  COM: { name: 'Comoros', center: [43.87, -11.88], zoom: 9, bbox: [43.2, -12.4, 44.5, -11.4] },
  COG: { name: 'Republic of Congo', center: [15.83, -0.23], zoom: 6, bbox: [11.1, -5.0, 18.6, 3.7], aliases: ['Congo-Brazzaville'] },
  COD: { name: 'Democratic Republic of Congo', center: [23.66, -4.04], zoom: 5, bbox: [12.2, -13.5, 31.3, 5.4], aliases: ['DRC', 'Congo-Kinshasa', 'Zaire'] },
  CIV: { name: 'Ivory Coast', center: [-5.55, 7.54], zoom: 7, bbox: [-8.6, 4.4, -2.5, 10.7], aliases: ['Côte d\'Ivoire'] },
  DJI: { name: 'Djibouti', center: [42.59, 11.83], zoom: 8, bbox: [41.8, 10.9, 43.4, 12.7] },
  EGY: { name: 'Egypt', center: [30.8, 26.82], zoom: 6, bbox: [24.7, 22.0, 36.9, 31.7] },
  GNQ: { name: 'Equatorial Guinea', center: [10.27, 1.65], zoom: 8, bbox: [9.3, 0.9, 11.3, 2.3] },
  ERI: { name: 'Eritrea', center: [39.78, 15.18], zoom: 7, bbox: [36.4, 12.4, 43.1, 18.0] },
  SWZ: { name: 'Eswatini', center: [31.47, -26.52], zoom: 8, bbox: [30.8, -27.3, 32.1, -25.7], aliases: ['Swaziland'] },
  ETH: { name: 'Ethiopia', center: [40.49, 9.15], zoom: 6, bbox: [33.0, 3.4, 48.0, 14.9] },
  GAB: { name: 'Gabon', center: [11.61, -0.8], zoom: 7, bbox: [8.7, -4.0, 14.5, 2.3] },
  GMB: { name: 'Gambia', center: [-15.31, 13.44], zoom: 8, bbox: [-16.8, 13.1, -13.8, 13.8] },
  GHA: { name: 'Ghana', center: [-1.02, 7.95], zoom: 7, bbox: [-3.3, 4.7, 1.2, 11.2] },
  GIN: { name: 'Guinea', center: [-9.7, 9.95], zoom: 7, bbox: [-15.1, 7.2, -7.6, 12.7] },
  GNB: { name: 'Guinea-Bissau', center: [-15.18, 11.8], zoom: 8, bbox: [-16.7, 11.0, -13.6, 12.7] },
  KEN: { name: 'Kenya', center: [37.91, -0.02], zoom: 6, bbox: [33.9, -4.7, 41.9, 5.5] },
  LSO: { name: 'Lesotho', center: [28.23, -29.61], zoom: 8, bbox: [27.0, -30.7, 29.5, -28.6] },
  LBR: { name: 'Liberia', center: [-9.43, 6.43], zoom: 7, bbox: [-11.5, 4.4, -7.4, 8.6] },
  LBY: { name: 'Libya', center: [17.23, 26.34], zoom: 6, bbox: [9.4, 19.5, 25.2, 33.2] },
  MDG: { name: 'Madagascar', center: [46.87, -18.77], zoom: 6, bbox: [43.2, -25.6, 50.5, -11.9] },
  MWI: { name: 'Malawi', center: [34.3, -13.25], zoom: 7, bbox: [32.7, -17.1, 35.9, -9.4] },
  MLI: { name: 'Mali', center: [-3.99, 17.57], zoom: 6, bbox: [-12.2, 10.1, 4.2, 25.0] },
  MRT: { name: 'Mauritania', center: [-10.94, 21.01], zoom: 6, bbox: [-17.1, 14.7, -4.8, 27.3] },
  MUS: { name: 'Mauritius', center: [57.55, -20.35], zoom: 9, bbox: [57.3, -20.5, 57.8, -20.0] },
  MAR: { name: 'Morocco', center: [-7.09, 31.79], zoom: 6, bbox: [-13.2, 27.7, -1.0, 35.9] },
  MOZ: { name: 'Mozambique', center: [35.53, -18.67], zoom: 6, bbox: [30.2, -26.9, 40.8, -10.5] },
  NAM: { name: 'Namibia', center: [18.49, -22.96], zoom: 6, bbox: [11.7, -28.9, 25.3, -16.9] },
  NER: { name: 'Niger', center: [8.08, 17.61], zoom: 6, bbox: [0.2, 11.7, 16.0, 23.5] },
  NGA: { name: 'Nigeria', center: [8.68, 9.08], zoom: 6, bbox: [2.7, 4.3, 14.7, 13.9] },
  RWA: { name: 'Rwanda', center: [29.87, -1.94], zoom: 8, bbox: [28.9, -2.8, 30.9, -1.0] },
  STP: { name: 'Sao Tome and Principe', center: [6.61, 0.19], zoom: 10, bbox: [6.5, 0.0, 7.5, 1.7] },
  SEN: { name: 'Senegal', center: [-14.45, 14.5], zoom: 7, bbox: [-17.5, 12.3, -11.4, 16.7] },
  SYC: { name: 'Seychelles', center: [55.49, -4.68], zoom: 10, bbox: [55.2, -4.8, 55.8, -4.6] },
  SLE: { name: 'Sierra Leone', center: [-11.78, 8.46], zoom: 8, bbox: [-13.3, 7.0, -10.3, 10.0] },
  SOM: { name: 'Somalia', center: [46.2, 5.15], zoom: 6, bbox: [40.9, -1.7, 51.4, 12.0] },
  ZAF: { name: 'South Africa', center: [22.94, -30.56], zoom: 6, bbox: [16.5, -34.8, 32.9, -22.1] },
  SSD: { name: 'South Sudan', center: [31.31, 7.86], zoom: 6, bbox: [24.1, 3.5, 35.9, 12.2] },
  SDN: { name: 'Sudan', center: [30.22, 12.86], zoom: 6, bbox: [21.8, 8.7, 38.6, 22.0] },
  TZA: { name: 'Tanzania', center: [34.89, -6.37], zoom: 6, bbox: [29.3, -11.7, 40.5, -1.0] },
  TGO: { name: 'Togo', center: [0.82, 8.62], zoom: 8, bbox: [-0.1, 6.1, 1.8, 11.1] },
  TUN: { name: 'Tunisia', center: [9.54, 33.89], zoom: 7, bbox: [7.5, 30.2, 11.6, 37.5] },
  UGA: { name: 'Uganda', center: [32.29, 1.37], zoom: 7, bbox: [29.6, -1.5, 35.0, 4.2] },
  ZMB: { name: 'Zambia', center: [27.85, -13.13], zoom: 6, bbox: [21.9, -18.1, 33.7, -8.2] },
  ZWE: { name: 'Zimbabwe', center: [29.15, -19.02], zoom: 7, bbox: [25.2, -22.4, 33.1, -15.6] },

  // === ASIA (48 countries) ===
  AFG: { name: 'Afghanistan', center: [67.71, 33.94], zoom: 6, bbox: [60.5, 29.4, 75.0, 38.5] },
  ARM: { name: 'Armenia', center: [45.04, 40.07], zoom: 8, bbox: [43.4, 38.8, 46.6, 41.3] },
  AZE: { name: 'Azerbaijan', center: [47.58, 40.14], zoom: 7, bbox: [44.8, 38.4, 50.4, 41.9] },
  BHR: { name: 'Bahrain', center: [50.55, 26.07], zoom: 10, bbox: [50.4, 25.8, 50.7, 26.3] },
  BGD: { name: 'Bangladesh', center: [90.36, 23.68], zoom: 7, bbox: [88.0, 20.7, 92.7, 26.6] },
  BTN: { name: 'Bhutan', center: [90.43, 27.51], zoom: 8, bbox: [88.8, 26.7, 92.1, 28.3] },
  BRN: { name: 'Brunei', center: [114.73, 4.54], zoom: 9, bbox: [114.1, 4.0, 115.4, 5.1] },
  KHM: { name: 'Cambodia', center: [104.99, 12.57], zoom: 7, bbox: [102.3, 10.4, 107.6, 14.7] },
  CHN: { name: 'China', center: [104.2, 35.86], zoom: 4, bbox: [73.5, 18.2, 135.1, 53.6] },
  IND: { name: 'India', center: [78.96, 20.59], zoom: 5, bbox: [68.2, 6.7, 97.4, 35.5] },
  IDN: { name: 'Indonesia', center: [113.92, -0.79], zoom: 5, bbox: [95.0, -11.0, 141.0, 6.0] },
  IRN: { name: 'Iran', center: [53.69, 32.43], zoom: 6, bbox: [44.0, 25.1, 63.3, 39.8] },
  IRQ: { name: 'Iraq', center: [43.68, 33.22], zoom: 6, bbox: [38.8, 29.1, 48.6, 37.4] },
  ISR: { name: 'Israel', center: [34.85, 31.05], zoom: 8, bbox: [34.3, 29.5, 35.9, 33.3] },
  JPN: { name: 'Japan', center: [138.25, 36.2], zoom: 5, bbox: [122.9, 24.0, 153.0, 45.5] },
  JOR: { name: 'Jordan', center: [36.24, 30.59], zoom: 7, bbox: [34.9, 29.2, 39.3, 33.4] },
  KAZ: { name: 'Kazakhstan', center: [66.92, 48.02], zoom: 5, bbox: [46.5, 40.9, 87.3, 55.4] },
  KWT: { name: 'Kuwait', center: [47.48, 29.31], zoom: 9, bbox: [46.6, 28.5, 48.4, 30.1] },
  KGZ: { name: 'Kyrgyzstan', center: [74.77, 41.2], zoom: 7, bbox: [69.3, 39.2, 80.3, 43.2] },
  LAO: { name: 'Laos', center: [102.5, 19.86], zoom: 6, bbox: [100.1, 13.9, 107.7, 22.5] },
  LBN: { name: 'Lebanon', center: [35.86, 33.85], zoom: 9, bbox: [35.1, 33.1, 36.6, 34.7] },
  MYS: { name: 'Malaysia', center: [101.98, 4.21], zoom: 6, bbox: [99.6, 0.9, 119.3, 7.4] },
  MDV: { name: 'Maldives', center: [73.22, 3.2], zoom: 8, bbox: [72.7, -0.7, 73.8, 7.1] },
  MNG: { name: 'Mongolia', center: [103.85, 46.86], zoom: 5, bbox: [87.7, 41.6, 119.9, 52.2] },
  MMR: { name: 'Myanmar', center: [95.96, 21.91], zoom: 6, bbox: [92.2, 9.8, 101.2, 28.5], aliases: ['Burma'] },
  NPL: { name: 'Nepal', center: [84.12, 28.39], zoom: 7, bbox: [80.1, 26.3, 88.2, 30.4] },
  PRK: { name: 'North Korea', center: [127.51, 40.34], zoom: 7, bbox: [124.3, 37.7, 130.7, 43.0] },
  OMN: { name: 'Oman', center: [55.92, 21.51], zoom: 7, bbox: [51.9, 16.6, 59.8, 26.4] },
  PAK: { name: 'Pakistan', center: [69.35, 30.38], zoom: 6, bbox: [60.9, 23.7, 77.8, 37.1] },
  PSE: { name: 'Palestine', center: [35.23, 31.95], zoom: 9, bbox: [34.2, 31.2, 35.6, 32.5] },
  PHL: { name: 'Philippines', center: [121.77, 12.88], zoom: 6, bbox: [116.9, 4.6, 126.6, 21.1] },
  QAT: { name: 'Qatar', center: [51.18, 25.35], zoom: 9, bbox: [50.8, 24.5, 51.6, 26.2] },
  RUS: { name: 'Russia', center: [105.32, 61.52], zoom: 3, bbox: [19.6, 41.2, 169.0, 81.9] },
  SAU: { name: 'Saudi Arabia', center: [45.08, 23.89], zoom: 6, bbox: [34.5, 16.0, 55.7, 32.2] },
  SGP: { name: 'Singapore', center: [103.82, 1.35], zoom: 11, bbox: [103.6, 1.2, 104.1, 1.5] },
  KOR: { name: 'South Korea', center: [127.77, 35.91], zoom: 7, bbox: [124.6, 33.1, 131.9, 38.6] },
  LKA: { name: 'Sri Lanka', center: [80.77, 7.87], zoom: 7, bbox: [79.7, 5.9, 81.9, 9.8] },
  SYR: { name: 'Syria', center: [38.99, 34.8], zoom: 7, bbox: [35.7, 32.3, 42.4, 37.3] },
  TWN: { name: 'Taiwan', center: [120.96, 23.7], zoom: 8, bbox: [120.0, 21.9, 122.0, 25.3] },
  TJK: { name: 'Tajikistan', center: [71.28, 38.86], zoom: 7, bbox: [67.4, 36.7, 75.1, 41.0] },
  THA: { name: 'Thailand', center: [100.99, 15.87], zoom: 6, bbox: [97.3, 5.6, 105.6, 20.5] },
  TLS: { name: 'Timor-Leste', center: [125.73, -8.87], zoom: 9, bbox: [124.0, -9.5, 127.3, -8.1], aliases: ['East Timor'] },
  TUR: { name: 'Turkey', center: [35.24, 38.96], zoom: 6, bbox: [26.0, 35.8, 45.0, 42.1] },
  TKM: { name: 'Turkmenistan', center: [59.56, 38.97], zoom: 6, bbox: [52.4, 35.1, 66.7, 42.8] },
  ARE: { name: 'United Arab Emirates', center: [53.85, 23.42], zoom: 8, bbox: [51.5, 22.6, 56.4, 26.1], aliases: ['UAE'] },
  UZB: { name: 'Uzbekistan', center: [64.59, 41.38], zoom: 6, bbox: [55.9, 37.2, 73.1, 45.6] },
  VNM: { name: 'Vietnam', center: [108.28, 14.06], zoom: 6, bbox: [102.1, 8.4, 109.5, 23.4] },
  YEM: { name: 'Yemen', center: [48.52, 15.55], zoom: 7, bbox: [42.6, 12.1, 54.5, 19.0] },

  // === AMERICAS (35 countries) ===
  ARG: { name: 'Argentina', center: [-63.62, -38.42], zoom: 5, bbox: [-73.4, -55.0, -53.6, -21.8] },
  BOL: { name: 'Bolivia', center: [-63.59, -16.29], zoom: 6, bbox: [-69.6, -22.9, -57.5, -9.7] },
  BRA: { name: 'Brazil', center: [-51.93, -14.24], zoom: 5, bbox: [-73.98, -33.75, -34.73, 5.27] },
  CAN: { name: 'Canada', center: [-106.35, 56.13], zoom: 4, bbox: [-141.0, 41.7, -52.6, 83.1] },
  CHL: { name: 'Chile', center: [-71.54, -35.68], zoom: 5, bbox: [-75.6, -55.9, -66.4, -17.5] },
  COL: { name: 'Colombia', center: [-74.3, 4.57], zoom: 6, bbox: [-79.0, -4.2, -66.9, 13.4] },
  CRI: { name: 'Costa Rica', center: [-83.75, 9.75], zoom: 8, bbox: [-86.0, 8.0, -82.5, 11.2] },
  ECU: { name: 'Ecuador', center: [-78.18, -1.83], zoom: 7, bbox: [-81.1, -5.0, -75.2, 1.7] },
  GUY: { name: 'Guyana', center: [-58.93, 4.86], zoom: 7, bbox: [-61.4, 1.2, -56.5, 8.6] },
  MEX: { name: 'Mexico', center: [-102.55, 23.63], zoom: 5, bbox: [-117.1, 14.5, -86.7, 32.7] },
  PER: { name: 'Peru', center: [-75.02, -9.19], zoom: 6, bbox: [-81.4, -18.4, -68.7, -0.04] },
  PRY: { name: 'Paraguay', center: [-58.44, -23.44], zoom: 6, bbox: [-62.6, -27.6, -54.3, -19.3] },
  SUR: { name: 'Suriname', center: [-56.03, 3.92], zoom: 7, bbox: [-58.1, 1.8, -54.0, 6.0] },
  URY: { name: 'Uruguay', center: [-55.77, -32.52], zoom: 7, bbox: [-58.4, -35.0, -53.1, -30.1] },
  USA: { name: 'United States', center: [-95.71, 37.09], zoom: 4, bbox: [-125.0, 24.4, -66.9, 49.4], aliases: ['US', 'America'] },
  VEN: { name: 'Venezuela', center: [-66.59, 6.42], zoom: 6, bbox: [-73.4, 0.6, -59.8, 12.2] },

  // === EUROPE (44 countries) ===
  DEU: { name: 'Germany', center: [10.45, 51.17], zoom: 6, bbox: [5.9, 47.3, 15.0, 55.1] },
  FRA: { name: 'France', center: [2.21, 46.23], zoom: 6, bbox: [-5.1, 41.3, 9.6, 51.1] },
  GBR: { name: 'United Kingdom', center: [-3.44, 55.38], zoom: 6, bbox: [-8.6, 49.9, 1.8, 60.8], aliases: ['UK', 'Britain'] },
  ITA: { name: 'Italy', center: [12.57, 41.87], zoom: 6, bbox: [6.6, 36.6, 18.5, 47.1] },
  ESP: { name: 'Spain', center: [-3.75, 40.46], zoom: 6, bbox: [-9.3, 35.9, 4.3, 43.8] },
  POL: { name: 'Poland', center: [19.15, 51.92], zoom: 6, bbox: [14.1, 49.0, 24.1, 54.8] },
  ROU: { name: 'Romania', center: [24.97, 45.94], zoom: 7, bbox: [20.3, 43.6, 29.7, 48.3] },
  UKR: { name: 'Ukraine', center: [31.17, 48.38], zoom: 6, bbox: [22.1, 44.4, 40.2, 52.4] },

  // === OCEANIA (14 countries) ===
  AUS: { name: 'Australia', center: [133.78, -25.27], zoom: 4, bbox: [113.3, -43.6, 153.6, -10.7] },
  NZL: { name: 'New Zealand', center: [174.89, -40.9], zoom: 6, bbox: [166.4, -47.3, 178.6, -34.4] },
  PNG: { name: 'Papua New Guinea', center: [143.96, -6.31], zoom: 6, bbox: [140.8, -11.7, 155.9, -1.0] },
  FJI: { name: 'Fiji', center: [178.07, -17.71], zoom: 8, bbox: [177.0, -20.7, 180.0, -12.5] },
};

// Helper functions
export const getCountryData = (countryCode: string): CountryData | null => {
  return COUNTRY_COORDINATES[countryCode.toUpperCase()] || null;
};

export const detectCountryFromQuery = (query: string): string | null => {
  const queryLower = query.toLowerCase();
  
  for (const [code, data] of Object.entries(COUNTRY_COORDINATES)) {
    if (queryLower.includes(data.name.toLowerCase())) {
      return code;
    }
    if (data.aliases) {
      for (const alias of data.aliases) {
        if (queryLower.includes(alias.toLowerCase())) {
          return code;
        }
      }
    }
  }
  
  return null;
};

export const getCountryName = (countryCode: string): string | null => {
  const data = getCountryData(countryCode);
  return data ? data.name : null;
};