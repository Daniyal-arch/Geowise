/**
 * Fire Detection Types
 * Matches backend NASA FIRMS API response
 */

export interface FireDetection {
  id: string;
  latitude: number;
  longitude: number;
  h3_index_9: string;
  h3_index_5: string;
  
  // Intensity metrics
  brightness: number;        // Kelvin (300-500K typical)
  bright_ti5?: number;       // Channel 5 brightness
  frp?: number;              // Fire Radiative Power (MW)
  
  // Detection metadata
  confidence: 'h' | 'n' | 'l';  // high, nominal, low
  satellite: string;         // 'N' = NOAA-20, 'T' = Terra, 'A' = Aqua
  instrument: string;        // VIIRS or MODIS
  
  // Temporal
  acq_date: string;          // ISO datetime
  acq_time: string;          // HHMM
  daynight: 'D' | 'N';       // Day or Night
  
  // Optional fields
  scan?: number;
  track?: number;
  version?: string;
}

export interface FireStatistics {
  total_fires: number;
  country: string;
  date_range: string;
  satellite: string;
  
  // Confidence breakdown
  high_confidence_count: number;
  nominal_confidence_count: number;
  low_confidence_count: number;
  
  // Intensity statistics
  frp_statistics: {
    avg: number;
    max: number;
    total: number;
  };
  brightness_statistics: {
    avg: number;
    max: number;
  };
  
  // Temporal analysis
  fires_by_date: Array<{
    date: string;
    count: number;
    avg_frp: number;
  }>;
  day_fires: number;
  night_fires: number;
  
  // Satellite coverage
  satellite_breakdown: Record<string, number>;
  
  last_updated: string;
}

export interface LiveFiresResponse {
  success: boolean;
  fires: FireDetection[];
  statistics: FireStatistics;
}