import { store } from './store.js';

export function setAccess(tokenVal) {
  store.token = tokenVal || null;
  if (window.api && typeof window.api.setAccessToken === 'function') {
    window.api.setAccessToken(store.token);
  }
}

export async function apiRequest(endpoint, options = {}) {
  const doCall = () => window.api.request(endpoint, options);

  try {
    const raw = await doCall();

    let env = raw;
    if (Array.isArray(raw)) {
      env = { status: 'ok', response: raw };
    } else if (raw && typeof raw.status === 'undefined') {
      env = raw.response !== undefined
        ? { status: 'ok', response: raw.response, message: raw.message || '' }
        : { status: 'ok', response: raw, message: '' };
    }

    if (env.status !== 'ok') {
      throw Object.assign(new Error(env.message || 'Unknown error'), { status: env.status || 500 });
    }
    return env.response;

  } catch (err) {
    const is401 = err && (err.status === 401 || /401/.test(String(err.message)));
    if (is401 && window.secureStore && window.auth && typeof window.auth.refresh === 'function') {
      try {
        const accountId = await window.secureStore.get('username');
        if (accountId) {
          const r = await window.auth.refresh(accountId); // { ok, access_token }
          if (r && r.ok && r.access_token) {
            setAccess(r.access_token);
            if (r.refresh_token && window.auth?.storeRefresh)
              await window.auth.storeRefresh(accountId, r.refresh_token);
            const raw2 = await doCall();
            let env2 = raw2;
            if (Array.isArray(raw2)) env2 = { status: 'ok', response: raw2 };
            else if (raw2 && typeof raw2.status === 'undefined') {
              env2 = raw2.response !== undefined
                ? { status: 'ok', response: raw2.response, message: raw2.message || '' }
                : { status: 'ok', response: raw2, message: '' };
            }
            if (env2.status !== 'ok') throw Object.assign(new Error(env2.message || 'Unknown error'), { status: env2.status || 500 });
            return env2.response;
          }
        }
      } catch (_) { /* fall through */ }
    }
    throw new Error(`Request failed: ${err.message || 'Unknown error'}`);
  }
}
