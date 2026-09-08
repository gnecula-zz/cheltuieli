/** Home Assistant Ingress prefix, empty when the app is served at domain root. */
export function getAppBasename(): string {
  const path = window.location.pathname;
  const ingress = path.match(/^(\/api\/hassio_ingress\/[^/]+)/);
  if (ingress) return ingress[1];
  const href = document.querySelector("base")?.getAttribute("href") || "";
  if (href && href !== "/" && href !== "./") {
    try {
      return new URL(href, window.location.origin).pathname.replace(/\/$/, "");
    } catch {
      return href.replace(/\/$/, "");
    }
  }
  return "";
}

export function apiUrl(path: string): string {
  const suffix = path.startsWith("/") ? path : `/${path}`;
  const withApi = suffix.startsWith("/api") ? suffix : `/api${suffix}`;
  return `${getAppBasename()}${withApi}`;
}
