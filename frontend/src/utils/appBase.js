/** 应用根路径（与 Vite base、Nginx location /tools/dsms/ 一致） */
export function appBasePath(env = import.meta.env) {
  const base = env.BASE_URL || "/";
  if (base === "/") return "/";
  return base.endsWith("/") ? base : `${base}/`;
}

/** 拼出带应用前缀的站内 URL（用于 location.href 等全页跳转） */
export function appUrl(path = "", env = import.meta.env) {
  const normalized = String(path || "").replace(/^\//, "");
  const base = appBasePath(env);
  if (base === "/") return `/${normalized}`;
  return `${base}${normalized}`;
}
