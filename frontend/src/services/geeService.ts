/**
 * GEE Service - Frontend API calls
 * Handles both Hansen tiles (ISO-3) and Driver tiles (ISO-2)
 */

const API_BASE_URL = 'http://localhost:8000/api/v1';

// ⭐ ISO-3 to ISO-2 conversion mapping for driver tiles
const ISO3_TO_ISO2: { [key: string]: string } = {
  'BRA': 'BR',  // Brazil
  'IDN': 'ID',  // Indonesia
  'COD': 'CD',  // DR Congo
  'COG': 'CG',  // Congo
  'PAK': 'PK',  // Pakistan
  'IND': 'IN',  // India
  'MYS': 'MY',  // Malaysia
  'MEX': 'MX',  // Mexico
  'PER': 'PE',  // Peru
  'COL': 'CO',  // Colombia
  'BOL': 'BO',  // Bolivia
  'VEN': 'VE',  // Venezuela
  'MMR': 'MM',  // Myanmar
  'THA': 'TH',  // Thailand
  'LAO': 'LA',  // Laos
  'KHM': 'KH',  // Cambodia
  'VNM': 'VN',  // Vietnam
  'PNG': 'PG',  // Papua New Guinea
  'CMR': 'CM',  // Cameroon
  'GAB': 'GA',  // Gabon
  'CAF': 'CF',  // Central African Republic
  'AGO': 'AO',  // Angola
  'ZMB': 'ZM',  // Zambia
  'TZA': 'TZ',  // Tanzania
  'MOZ': 'MZ',  // Mozambique
  'MDG': 'MG',  // Madagascar
  'NGA': 'NG',  // Nigeria
  'GHA': 'GH',  // Ghana
  'CIV': 'CI',  // Ivory Coast
  'LBR': 'LR',  // Liberia
  'SLE': 'SL',  // Sierra Leone
  'GIN': 'GN',  // Guinea
  'SEN': 'SN',  // Senegal
  'ETH': 'ET',  // Ethiopia
  'KEN': 'KE',  // Kenya
  'UGA': 'UG',  // Uganda
  'RWA': 'RW',  // Rwanda
  'BDI': 'BI',  // Burundi
  'SOM': 'SO',  // Somalia
  'SDN': 'SD',  // Sudan
  'SSD': 'SS',  // South Sudan
  'TCD': 'TD',  // Chad
  'NER': 'NE',  // Niger
  'MLI': 'ML',  // Mali
  'BFA': 'BF',  // Burkina Faso
  'BEN': 'BJ',  // Benin
  'TGO': 'TG',  // Togo
  'ZAF': 'ZA',  // South Africa
  'ZWE': 'ZW',  // Zimbabwe
  'BWA': 'BW',  // Botswana
  'NAM': 'NA',  // Namibia
  'SWZ': 'SZ',  // Eswatini
  'LSO': 'LS',  // Lesotho
  'MWI': 'MW',  // Malawi
  'USA': 'US',  // United States
  'CAN': 'CA',  // Canada
  'AUS': 'AU',  // Australia
  'NZL': 'NZ',  // New Zealand
  'CHN': 'CN',  // China
  'JPN': 'JP',  // Japan
  'KOR': 'KR',  // South Korea
  'PRK': 'KP',  // North Korea
  'MNG': 'MN',  // Mongolia
  'BGD': 'BD',  // Bangladesh
  'NPL': 'NP',  // Nepal
  'BTN': 'BT',  // Bhutan
  'LKA': 'LK',  // Sri Lanka
  'PHL': 'PH',  // Philippines
  'TWN': 'TW',  // Taiwan
  'KAZ': 'KZ',  // Kazakhstan
  'UZB': 'UZ',  // Uzbekistan
  'TKM': 'TM',  // Turkmenistan
  'KGZ': 'KG',  // Kyrgyzstan
  'TJK': 'TJ',  // Tajikistan
  'AFG': 'AF',  // Afghanistan
  'IRN': 'IR',  // Iran
  'IRQ': 'IQ',  // Iraq
  'SYR': 'SY',  // Syria
  'TUR': 'TR',  // Turkey
  'SAU': 'SA',  // Saudi Arabia
  'YEM': 'YE',  // Yemen
  'OMN': 'OM',  // Oman
  'ARE': 'AE',  // UAE
  'QAT': 'QA',  // Qatar
  'KWT': 'KW',  // Kuwait
  'BHR': 'BH',  // Bahrain
  'JOR': 'JO',  // Jordan
  'LBN': 'LB',  // Lebanon
  'ISR': 'IL',  // Israel
  'PSE': 'PS',  // Palestine
  'EGY': 'EG',  // Egypt
  'LBY': 'LY',  // Libya
  'TUN': 'TN',  // Tunisia
  'DZA': 'DZ',  // Algeria
  'MAR': 'MA',  // Morocco
  'MRT': 'MR',  // Mauritania
  'ESH': 'EH',  // Western Sahara
  'RUS': 'RU',  // Russia
  'UKR': 'UA',  // Ukraine
  'BLR': 'BY',  // Belarus
  'POL': 'PL',  // Poland
  'CZE': 'CZ',  // Czech Republic
  'SVK': 'SK',  // Slovakia
  'HUN': 'HU',  // Hungary
  'ROU': 'RO',  // Romania
  'BGR': 'BG',  // Bulgaria
  'SRB': 'RS',  // Serbia
  'HRV': 'HR',  // Croatia
  'BIH': 'BA',  // Bosnia
  'MNE': 'ME',  // Montenegro
  'MKD': 'MK',  // North Macedonia
  'ALB': 'AL',  // Albania
  'GRC': 'GR',  // Greece
  'ITA': 'IT',  // Italy
  'ESP': 'ES',  // Spain
  'PRT': 'PT',  // Portugal
  'FRA': 'FR',  // France
  'DEU': 'DE',  // Germany
  'GBR': 'GB',  // United Kingdom
  'IRL': 'IE',  // Ireland
  'NLD': 'NL',  // Netherlands
  'BEL': 'BE',  // Belgium
  'LUX': 'LU',  // Luxembourg
  'CHE': 'CH',  // Switzerland
  'AUT': 'AT',  // Austria
  'DNK': 'DK',  // Denmark
  'SWE': 'SE',  // Sweden
  'NOR': 'NO',  // Norway
  'FIN': 'FI',  // Finland
  'ISL': 'IS',  // Iceland
  'EST': 'EE',  // Estonia
  'LVA': 'LV',  // Latvia
  'LTU': 'LT',  // Lithuania
  'SVN': 'SI',  // Slovenia
  'ARG': 'AR',  // Argentina
  'CHL': 'CL',  // Chile
  'URY': 'UY',  // Uruguay
  'PRY': 'PY',  // Paraguay
  'ECU': 'EC',  // Ecuador
  'GUY': 'GY',  // Guyana
  'SUR': 'SR',  // Suriname
  'GUF': 'GF',  // French Guiana
};

/**
 * Convert ISO-3 country code to ISO-2
 */
function convertISO3toISO2(iso3: string): string {
  const iso2 = ISO3_TO_ISO2[iso3.toUpperCase()];
  if (!iso2) {
    console.warn(`[GEE Service] No ISO-2 mapping for ${iso3}, using first 2 letters`);
    return iso3.substring(0, 2).toUpperCase();
  }
  return iso2;
}

export interface HansenForestTiles {
  success: boolean;
  country_iso: string;
  country_name: string;
  center: [number, number];
  zoom: number;
  layers: {
    baseline: { name: string; tile_url: string; description: string; year_range: string };
    loss: { name: string; tile_url: string; description: string; year_range: string };
    gain: { name: string; tile_url: string; description: string; year_range: string };
  };
  generated_at: string;
}

export interface DriverTiles {
  success: boolean;
  country_iso: string;
  driver_type: string;
  tile_url: string;
  driver_categories: {
    [key: number]: {
      name: string;
      color: string;
      description: string;
    };
  };
  dataset_info: {
    source: string;
    resolution: string;
    year: string;
    citation: string;
  };
}

/**
 * Get Hansen Forest Change tiles (baseline/loss/gain)
 * Uses ISO-3 country codes
 */
export async function getHansenForestTiles(countryISO: string): Promise<HansenForestTiles> {
  const url = `${API_BASE_URL}/gee/tiles/${countryISO.toUpperCase()}`;
  
  console.log('[GEE Service] Fetching Hansen tiles for:', countryISO);
  
  const response = await fetch(url);
  
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}: ${await response.text()}`);
  }
  
  const data = await response.json();
  
  console.log('[GEE Service] ✅ Tiles received:', {
    success: data.success,
    country_iso: data.country_iso,
    country_name: data.country_name,
    center: data.center,
    zoom: data.zoom
  });
  
  return data;
}

/**
 * Get Driver tiles (deforestation causes)
 * ⭐ Converts ISO-3 to ISO-2 automatically
 */
export async function getDriverTiles(countryISO: string): Promise<DriverTiles> {
  // ⭐ Convert ISO-3 to ISO-2 for driver API
  const iso2 = convertISO3toISO2(countryISO);
  
  const url = `${API_BASE_URL}/tiles/${iso2}/drivers`;
  
  console.log(`[GEE Service] Fetching driver tiles for: ${countryISO} (converted to ${iso2})`);
  
  const response = await fetch(url);
  
  if (!response.ok) {
    const errorText = await response.text();
    throw new Error(`HTTP ${response.status}: ${errorText}`);
  }
  
  const data = await response.json();
  
  console.log('[GEE Service] ✅ Driver tiles received:', {
    success: data.success,
    country_iso: data.country_iso,
    categories: Object.keys(data.driver_categories).length
  });
  
  return data;
}