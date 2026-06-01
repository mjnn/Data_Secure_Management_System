/** Refresh token 单飞与 401 重试协调（便于单测） */

export function createRefreshCoordinator() {
  let refreshPromise = null;

  return {
    async run(refreshFn) {
      if (!refreshPromise) {
        refreshPromise = refreshFn().finally(() => {
          refreshPromise = null;
        });
      }
      return refreshPromise;
    },
    reset() {
      refreshPromise = null;
    },
    get pending() {
      return refreshPromise != null;
    }
  };
}

/**
 * @param {object} opts
 * @param {import('axios').AxiosError} opts.error
 * @param {import('axios').AxiosInstance} opts.api
 * @param {ReturnType<typeof createRefreshCoordinator>} opts.coordinator
 * @param {() => string | null} opts.getRefreshToken
 * @param {() => Promise<string>} opts.refreshAccessToken
 * @param {() => void} opts.onAuthFailure
 */
export async function handleUnauthorizedResponse({
  error,
  api,
  coordinator,
  getRefreshToken,
  refreshAccessToken,
  onAuthFailure
}) {
  const original = error.config;
  if (error.response?.status !== 401 || !original || original._retry) {
    return null;
  }

  const refreshToken = getRefreshToken();
  if (!refreshToken) {
    onAuthFailure();
    return null;
  }

  original._retry = true;
  try {
    const accessToken = await coordinator.run(refreshAccessToken);
    original.headers.Authorization = `Bearer ${accessToken}`;
    return api.request(original);
  } catch {
    onAuthFailure();
    return null;
  }
}
