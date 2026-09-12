const puppeteer = require('puppeteer-core');

const CHROME = '/root/.cache/puppeteer/chrome-headless-shell/linux-151.0.7922.71/chrome-headless-shell-linux64/chrome-headless-shell';
const BASE = 'http://127.0.0.1:5173';

const STORY = '古风仙侠故事：青云宗弟子陆凡在宗门大比中被同门陷害坠入悬崖，却意外获得上古剑诀，三年后化名林尘重回宗门复仇，夺回属于自己的掌门之位。';

(async () => {
  const browser = await puppeteer.launch({
    executablePath: CHROME,
    headless: 'new',
    args: ['--no-sandbox', '--disable-setuid-sandbox', '--disable-gpu'],
  });
  const page = await browser.newPage();
  await page.setViewport({ width: 1440, height: 900 });

  const consoleErrors = [];
  page.on('console', (msg) => {
    if (msg.type() === 'error') consoleErrors.push(msg.text());
  });
  page.on('pageerror', (err) => consoleErrors.push('PAGEERROR: ' + err.message));

  await page.goto(BASE, { waitUntil: 'networkidle2', timeout: 30000 });
  await page.waitForFunction(() => window.ApiClient && window.openScript && window.parseImport, { timeout: 20000 });

  // 1) 注册 + 创建剧本（走前端自身 ApiClient，确保 token 注入 localStorage）
  const user = 'browser_' + Date.now().toString(36);
  const setup = await page.evaluate(async (user) => {
    const reg = await ApiClient.auth.register(user, 'pass1234', '浏览器测试');
    const s = await ApiClient.scripts.create({ title: '全流程浏览器验证', path_type: 'B', config: {}, step: 0, progress: 0, status: 'draft' });
    await window.openScript(s.id);
    return { token: reg.access_token, scriptId: s.id };
  }, user);

  // 2) 填文本 + 触发导入解析（走真实 UI 桥函数 window.parseImport）
  await page.evaluate((story) => {
    const el = document.getElementById('impText');
    el.value = story;
    const ev = new Event('input', { bubbles: true });
    el.dispatchEvent(ev);
  }, STORY);

  await page.evaluate(() => window.parseImport());

  // 3) 轮询等待 outlineData 被文本派生结果替换（检测到「仙侠/修仙」题材关键字）
  const ok = await page.waitForFunction(() => {
    if (!Array.isArray(window.outlineData) || !window.outlineData.length) return false;
    const joined = window.outlineData.map(m => (m.summary || '') + ' ' + (m.content || '')).join(' ');
    return /仙侠|修仙|玄幻|陆凡|林尘/.test(joined);
  }, { timeout: 60000, polling: 2000 }).then(() => true).catch(() => false);

  // 4) 取最终状态
  const state = await page.evaluate(() => ({
    outline: (window.outlineData || []).map(m => ({ id: m.id, title: m.title, summary: m.summary, content: (m.content || '').slice(0, 80) })),
    characters: (window.characterData || []).map(c => ({ name: c.name, role: c.role })),
    episodes: (window.episodes || []).length,
    detected: window.__detected || null,
  }));

  await page.screenshot({ path: '/workspace/.browsertest/result.png', fullPage: true });
  await browser.close();

  console.log('SETUP_OK token=' + (setup.token ? 'yes' : 'no') + ' scriptId=' + setup.scriptId);
  console.log('OUTLINE_UPDATED=' + ok);
  console.log('OUTLINE:', JSON.stringify(state.outline, null, 2));
  console.log('CHARACTERS:', JSON.stringify(state.characters));
  console.log('EPISODES_COUNT:', state.episodes);
  console.log('CONSOLE_ERRORS:', consoleErrors.length ? JSON.stringify(consoleErrors.slice(0, 5)) : 'none');

  if (!ok) {
    console.log('RESULT: FAIL - outline 未更新为文本派生内容');
    process.exit(1);
  }
  const joined = state.outline.map(m => (m.summary || '') + ' ' + (m.content || '')).join(' ');
  if (/苏晚晴|豪门复仇/.test(joined)) {
    console.log('RESULT: FAIL - 仍出现静态豪门内容');
    process.exit(1);
  }
  console.log('RESULT: PASS - 全流程浏览器验证通过（文本派生大纲/人物已回写渲染）');
})().catch((e) => {
  console.error('TEST_ERROR:', e && e.message ? e.message : e);
  process.exit(2);
});
