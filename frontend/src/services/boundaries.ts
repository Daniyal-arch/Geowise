/**
 * Country Boundary Service
 * Fetches country boundaries from Natural Earth via CDN
 * Uses SOV_A3 field for ISO code matching
 */

interface CountryBoundary {
  type: 'FeatureCollection';
  features: Array<{
    type: 'Feature';
    properties: any;
    geometry: {
      type: 'Polygon' | 'MultiPolygon';
      coordinates: any;
    };
  }>;
}

// Cache to avoid repeated fetches
const boundaryCache = new Map<string, CountryBoundary>();

// CDN URL for Natural Earth 10m countries (using jsdelivr CDN)
const NATURAL_EARTH_URL = 'https://cdn.jsdelivr.net/gh/nvkelso/natural-earth-vector@master/geojson/ne_10m_admin_0_countries.geojson';

/**
 * Fetch country boundary GeoJSON by ISO code
 * @param countryISO - 3-letter ISO code (e.g., 'BRA', 'IDN')
 * @returns Country boundary GeoJSON or null if not found
 */
export async function getCountryBoundary(countryISO: string): Promise<CountryBoundary | null> {
  try {
    const isoUpper = countryISO.toUpperCase();
    
    // Check cache first
    if (boundaryCache.has(isoUpper)) {
      console.log('[Boundaries] ✅ Boundary cached for:', isoUpper);
      return boundaryCache.get(isoUpper)!;
    }
    
    console.log('[Boundary] Fetching boundary for:', isoUpper);
    
    // Fetch all countries
    const response = await fetch(NATURAL_EARTH_URL);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }
    
    const allCountries = await response.json();
    
    // Find country by SOV_A3 field (primary), with fallbacks
    let countryFeature = allCountries.features.find(
      (feature: any) => feature.properties.SOV_A3 === isoUpper
    );
    
    // Fallback 1: Try ADM0_A3
    if (!countryFeature) {
      countryFeature = allCountries.features.find(
        (feature: any) => feature.properties.ADM0_A3 === isoUpper
      );
    }
    
    // Fallback 2: Try ISO_A3
    if (!countryFeature) {
      countryFeature = allCountries.features.find(
        (feature: any) => feature.properties.ISO_A3 === isoUpper
      );
    }
    
    // Fallback 3: Name matching for special cases
    if (!countryFeature) {
      const nameMap: { [key: string]: string } = {
        'COD': 'Democratic Republic of the Congo',
        'COG': 'Republic of the Congo',
        'CIV': "Côte d'Ivoire"
      };
      
      if (nameMap[isoUpper]) {
        countryFeature = allCountries.features.find(
          (feature: any) => feature.properties.NAME === nameMap[isoUpper] ||
                           feature.properties.SOVEREIGNT === nameMap[isoUpper]
        );
      }
    }
    
    if (!countryFeature) {
      console.error('[Boundaries] Country not found in dataset:', isoUpper);
      console.log('[Boundaries] Available properties sample:', 
        allCountries.features[0]?.properties
      );
      return null;
    }
    
    console.log('[Boundaries] ✅ Found using SOV_A3:', isoUpper);
    
    // Create boundary object
    const boundary: CountryBoundary = {
      type: 'FeatureCollection',
      features: [countryFeature]
    };
    
    // Cache it
    boundaryCache.set(isoUpper, boundary);
    
    return boundary;
    
  } catch (error) {
    console.error('[Boundaries] Error fetching boundary:', error);
    return null;
  }
}

/**
 * Clear the boundary cache (useful for testing)
 */
export function clearBoundaryCache(): void {
  boundaryCache.clear();
  console.log('[Boundaries] Cache cleared');
}