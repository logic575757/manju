/* ========== API Client (src/api.js) ==========
 * 提供 auth / scripts / ai / tags / imports 五组封装
 * - 自动注入 JWT
 * - 401 自动登出
 * - SSE 流式（fetch + ReadableStream 解析 SSE 协议）
 */

const TOKEN_KEY = 'script_auth_token_v1';
const USER_KEY = 'script_auth_user_v1';

const ApiClient = (() => {
  function getToken() {
    try { return localStorage.getItem(TOKEN_KEY); } catch (e) { return null; }
  }
  function setToken(t) {
    if (t) localStorage.setItem(TOKEN_KEY, t);
    else localStorage.removeItem(TOKEN_KEY);
  }
  function getUser() {
    try { return JSON.parse(localStorage.getItem(USER_KEY) || 'null'); } catch (e) { return null; }
  }
  function setUser(u) {
    if (u) localStorage.setItem(USER_KEY, JSON.stringify(u));
    else localStorage.removeItem(USER_KEY);
  }
  function clearAuth() {
    setToken(null); setUser(null);
  }
  function isLoggedIn() { return !!getToken(); }

  async function request(path, opts = {}) {
    const { method = 'GET', body, query, headers = {} } = opts;
    let url = path;
    if (query) {
      const qs = new URLSearchParams(
        Object.entries(query).filter(([, v]) => v !== undefined && v !== null)
      ).toString();
      if (qs) url += (url.includes('?') ? '&' : '?') + qs;
    }
    const finalHeaders = { 'Content-Type': 'application/json', ...headers };
    const token = getToken();
    if (token) finalHeaders['Authorization'] = `Bearer ${token}`;
    const resp = await fetch(url, {
      method,
      headers: finalHeaders,
      body: body !== undefined ? (typeof body === 'string' ? body : JSON.stringify(body)) : undefined,
    });
    if (resp.status === 401) {
      clearAuth();
      if (window.__onAuthFail) window.__onAuthFail();
      throw new Error('未登录或登录已过期');
    }
    const ct = resp.headers.get('content-type') || '';
    if (!resp.ok) {
      let detail = resp.statusText;
      try {
        if (ct.includes('application/json')) {
          const j = await resp.json();
          detail = j.detail || j.message || JSON.stringify(j);
        } else {
          detail = await resp.text();
        }
      } catch (e) {}
      const err = new Error(detail);
      err.status = resp.status;
      throw err;
    }
    if (ct.includes('application/json')) return resp.json();
    return resp.text();
  }

  /* -------- SSE 流式（POST + ReadableStream 解析） -------- */
  /**
   * 以 SSE 方式 POST 一个 JSON body 到 path，按事件回调。
   * handlers: { onPhase, onDelta, onProgress, onResult, onModule, onDone, onError }
   * 返回 AbortController 方便中止。
   */
  function streamSSE(path, body, handlers = {}) {
    const controller = new AbortController();
    const token = getToken();
    (async () => {
      try {
        const resp = await fetch(path, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'text/event-stream',
            ...(token ? { 'Authorization': `Bearer ${token}` } : {}),
          },
          body: JSON.stringify(body || {}),
          signal: controller.signal,
        });
        if (resp.status === 401) {
          clearAuth();
          if (window.__onAuthFail) window.__onAuthFail();
          if (handlers.onError) handlers.onError(new Error('未登录或登录已过期'));
          return;
        }
        if (!resp.ok || !resp.body) {
          const text = await resp.text().catch(() => '');
          throw new Error(text || `HTTP ${resp.status}`);
        }
        const reader = resp.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buf = '';
        let eventName = 'message';
        let dataLines = [];
        function dispatch() {
          if (!dataLines.length) { eventName = 'message'; return; }
          const dataStr = dataLines.join('\n');
          dataLines = [];
          let parsed;
          try { parsed = dataStr === '' ? '' : JSON.parse(dataStr); } catch (e) { parsed = dataStr; }
          try {
            if (eventName === 'phase' && handlers.onPhase) handlers.onPhase(parsed);
            else if (eventName === 'delta' && handlers.onDelta) handlers.onDelta(parsed);
            else if (eventName === 'progress' && handlers.onProgress) handlers.onProgress(parsed);
            else if (eventName === 'result' && handlers.onResult) handlers.onResult(parsed);
            else if (eventName === 'module' && handlers.onModule) handlers.onModule(parsed);
            else if (eventName === 'done') {
              if (handlers.onDone) handlers.onDone(parsed);
            } else if (eventName === 'error') {
              if (handlers.onError) handlers.onError(new Error(parsed?.message || parsed || 'AI 调用失败'));
            }
          } catch (cbErr) {
            console.error('SSE handler error:', cbErr);
          }
          eventName = 'message';
        }
        while (true) {
          const { value, done } = await reader.read();
          if (done) break;
          buf += decoder.decode(value, { stream: true });
          let idx;
          while ((idx = buf.indexOf('\n')) !== -1) {
            const line = buf.slice(0, idx).replace(/\r$/, '');
            buf = buf.slice(idx + 1);
            if (line === '') { dispatch(); continue; }
            if (line.startsWith(':')) continue;
            if (line.startsWith('event:')) {
              eventName = line.slice(6).trim();
            } else if (line.startsWith('data:')) {
              dataLines.push(line.slice(5).replace(/^\s/, ''));
            }
          }
        }
        dispatch();
      } catch (err) {
        if (err.name === 'AbortError') return;
        console.error('SSE error:', err);
        if (handlers.onError) handlers.onError(err);
      }
    })();
    return controller;
  }

  /* ============== auth ============== */
  const auth = {
    async register(username, password, nickname) {
      const data = await request('/api/auth/register', { method: 'POST', body: { username, password, display_name: nickname } });
      if (data.access_token) { setToken(data.access_token); setUser(data.user); }
      return data;
    },
    async login(username, password) {
      const resp = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });
      if (resp.status === 401) throw new Error('用户名或密码错误');
      if (!resp.ok) {
        let msg = '登录失败';
        try { msg = (await resp.json()).detail || msg; } catch(e){}
        throw new Error(msg);
      }
      const data = await resp.json();
      if (data.access_token) { setToken(data.access_token); setUser(data.user); }
      return data;
    },
    async me() {
      const data = await request('/api/auth/me');
      setUser(data);
      return data;
    },
    logout() { clearAuth(); },
    isLoggedIn,
    getUser,
    getToken,
  };

  /* ============== scripts ============== */
  const scripts = {
    list(params = {}) { return request('/api/scripts', { query: params }); },
    get(id) { return request(`/api/scripts/${id}`); },
    create(body) { return request('/api/scripts', { method: 'POST', body }); },
    update(id, patch) { return request(`/api/scripts/${id}`, { method: 'PATCH', body: patch }); },
    remove(id, permanent = false) {
      return request(`/api/scripts/${id}`, { method: 'DELETE', query: permanent ? { permanent: 'true' } : {} });
    },
    restore(id) { return request(`/api/scripts/${id}/restore`, { method: 'POST' }); },
    duplicate(id) { return request(`/api/scripts/${id}/duplicate`, { method: 'POST' }); },
    lock(id, finalName) { return request(`/api/scripts/${id}/lock`, { method: 'POST', body: { name: finalName || '' } }); },
    unlock(id) { return request(`/api/scripts/${id}/unlock`, { method: 'POST' }); },
    export(id, format = 'json', versionId = null) {
      return request(`/api/scripts/${id}/export`, { query: { format, version_id: versionId } });
    },
    versions(id) { return request(`/api/scripts/${id}/versions`); },
    createVersion(id, note = '') {
      return request(`/api/scripts/${id}/versions`, { method: 'POST', body: { note } });
    },
    getVersion(id, vid) { return request(`/api/scripts/${id}/versions/${vid}`); },
    restoreVersion(id, vid) { return request(`/api/scripts/${id}/versions/${vid}/restore`, { method: 'POST' }); },
    deleteVersion(id, vid) { return request(`/api/scripts/${id}/versions/${vid}`, { method: 'DELETE' }); },
    diff(id, v1, v2) { return request(`/api/scripts/${id}/versions/diff`, { query: { v1, v2 } }); },
  };

  /* ============== AI (队列提交，返回任务回执) ============== */
  const ai = {
    generateOutline(scriptId, params) {
      return request('/api/ai/outline/generate', { method: 'POST', body: { script_id: scriptId, ...params } });
    },
    reviewOutline(scriptId, outline) {
      return request('/api/ai/outline/review', { method: 'POST', body: { script_id: scriptId, outline } });
    },
    modifyModule(scriptId, moduleId, module, note, issues) {
      return request('/api/ai/outline/modify-module', {
        method: 'POST',
        body: { script_id: scriptId, module_id: moduleId, module, note: note || '', issues },
      });
    },
    batchModify(scriptId, modules, globalNote) {
      return request('/api/ai/outline/batch-modify', {
        method: 'POST',
        body: { script_id: scriptId, modules, global_note: globalNote || '' },
      });
    },
    generateCharacters(scriptId, outline, existingCharacters) {
      return request('/api/ai/characters/generate', {
        method: 'POST',
        body: { script_id: scriptId, outline, existing_characters: existingCharacters || [] },
      });
    },
    reviewCharacters(scriptId, characters, outline) {
      return request('/api/ai/characters/review', {
        method: 'POST',
        body: { script_id: scriptId, characters, outline: outline || null },
      });
    },
    generateEpisode(scriptId, episodeIndex, outline, characters, previousEpisodes) {
      return request('/api/ai/episode/generate', {
        method: 'POST',
        body: { script_id: scriptId, episode_index: episodeIndex, outline, characters, previous_episodes: previousEpisodes || [] },
      });
    },
    reviewEpisode(scriptId, episodeIndex, episode, outline, characters, previousEpisodes) {
      return request('/api/ai/episode/review', {
        method: 'POST',
        body: { script_id: scriptId, episode_index: episodeIndex, episode, outline: outline || null, characters: characters || null, previous_episodes: previousEpisodes || [] },
      });
    },
    fixEpisode(scriptId, episodeIndex, episode, issues) {
      return request('/api/ai/episode/fix', {
        method: 'POST',
        body: { script_id: scriptId, episode_index: episodeIndex, episode, issues },
      });
    },
    rewriteSegment(scriptId, episodeIndex, behavior, instruction, candidates) {
      return request('/api/ai/episode/rewrite-segment', {
        method: 'POST',
        body: { script_id: scriptId, episode_index: episodeIndex, behavior, instruction, candidates: candidates || 2 },
      });
    },
    parseImport(scriptId, text, file_name, episodes, ep_duration, tone) {
      return request('/api/ai/import/parse', {
        method: 'POST',
        body: { text, file_name: file_name || '', episodes: episodes || 20, ep_duration: ep_duration || 90, tone: tone || '保持原作风味', script_id: scriptId || null },
      });
    },
  };

  /* ============== AI 任务（队列轮询 / 管理） ============== */
  const tasks = {
    list(params = {}) { return request('/api/ai/tasks', { query: params }); },
    get(id, includeEvents = false) {
      return request(`/api/ai/tasks/${id}`, { query: includeEvents ? { include_events: 'true' } : {} });
    },
    cancel(id) { return request(`/api/ai/tasks/${id}/cancel`, { method: 'POST' }); },
    retry(id) { return request(`/api/ai/tasks/${id}/retry`, { method: 'POST' }); },
    remove(id) { return request(`/api/ai/tasks/${id}`, { method: 'DELETE' }); },
    stats() { return request('/api/ai/tasks/stats'); },
  };

  /* ============== tags ============== */
  const tags = {
    list(category) { return request('/api/tags', { query: category ? { category } : {} }); },
    categories() { return request('/api/tags/categories'); },
  };

  /* ============== imports ============== */
  const imports = {
    async upload(title, file, scriptId = null, onProgress) {
      return new Promise((resolve, reject) => {
        const xhr = new XMLHttpRequest();
        const fd = new FormData();
        fd.append('title', title);
        fd.append('file', file);
        if (scriptId) fd.append('script_id', scriptId);
        xhr.open('POST', '/api/imports');
        const token = getToken();
        if (token) xhr.setRequestHeader('Authorization', `Bearer ${token}`);
        xhr.upload.onprogress = (e) => {
          if (e.lengthComputable && onProgress) onProgress(e.loaded / e.total);
        };
        xhr.onload = () => {
          if (xhr.status >= 200 && xhr.status < 300) {
            try { resolve(JSON.parse(xhr.responseText)); } catch (e) { resolve(xhr.responseText); }
          } else {
            reject(new Error(xhr.responseText || `HTTP ${xhr.status}`));
          }
        };
        xhr.onerror = () => reject(new Error('网络错误'));
        xhr.send(fd);
      });
    },
    list(scriptId) { return request('/api/imports', { query: scriptId ? { script_id: scriptId } : {} }); },
  };

  return { auth, scripts, ai, tasks, tags, imports, getToken, isLoggedIn, clearAuth };
})();

window.ApiClient = ApiClient;
