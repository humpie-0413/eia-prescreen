/** South Korea latitude range */
const LAT_MIN = 33;
const LAT_MAX = 43;

/** South Korea longitude range */
const LNG_MIN = 124;
const LNG_MAX = 132;

export interface CoordError {
  lat?: string;
  lng?: string;
}

export function validateCoordinates(
  lat: number | null | undefined,
  lng: number | null | undefined,
): CoordError {
  const errors: CoordError = {};

  if (lat != null) {
    if (isNaN(lat)) {
      errors.lat = "위도는 숫자여야 합니다.";
    } else if (lat < LAT_MIN || lat > LAT_MAX) {
      errors.lat = `위도는 ${LAT_MIN}~${LAT_MAX} 범위여야 합니다.`;
    }
  }

  if (lng != null) {
    if (isNaN(lng)) {
      errors.lng = "경도는 숫자여야 합니다.";
    } else if (lng < LNG_MIN || lng > LNG_MAX) {
      errors.lng = `경도는 ${LNG_MIN}~${LNG_MAX} 범위여야 합니다.`;
    }
  }

  return errors;
}

export function hasCoordErrors(errors: CoordError): boolean {
  return Boolean(errors.lat || errors.lng);
}
