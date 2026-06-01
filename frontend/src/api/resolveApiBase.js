/** 解析 axios baseURL（开发走 Vite 代理，生产/ECS 跟随 BASE_URL） */

/**
 * @param {ImportMetaEnv} env
 * @returns {string}
 */
export function resolveApiBase(env) {
  if (env.VITE_API_BASE != null && env.VITE_API_BASE !== "") {
    return env.VITE_API_BASE;
  }
  if (env.DEV) return "";
  const base = env.BASE_URL || "/";
  return base === "/" ? "" : base.replace(/\/$/, "");
}
