// GACOS 批量提交脚本 v2：node gacos_submit.js <批号1-4>
const { chromium } = require('D:/development/NodeJS/node_modules/@playwright/mcp/node_modules/playwright-core');
const fs = require('fs');
const path = require('path');

const batch = process.argv[2];
if (!batch) { console.error('用法: node gacos_submit.js <批号>'); process.exit(1); }
const dates = fs.readFileSync(path.join('D:/work/data/配套数据', `gacos_batch${batch}.txt`), 'utf8').trim().split('\n');
console.log(`批 ${batch}: ${dates.length} 个日期, 首个 ${dates[0]}, 末个 ${dates[dates.length-1]}`);

(async () => {
  const browser = await chromium.launch({ headless: true });
  const page = await browser.newPage();
  await page.goto('http://www.gacos.net/index.html', { timeout: 120000, waitUntil: 'domcontentloaded' });
  await page.waitForTimeout(6000);

  // 研究区范围（古浪 +0.1 缓冲）—— 用 name 选择器
  await page.locator('input[name="N"]').fill('38.34', { timeout: 15000 });
  await page.locator('input[name="W"]').fill('101.96');
  await page.locator('input[name="E"]').fill('103.48');
  await page.locator('input[name="S"]').fill('37.28');
  // UTC 时刻 23:10
  await page.locator('select[name="H"]').selectOption('23');
  await page.locator('select[name="M"]').selectOption('10');
  // 日期列表（textarea）
  await page.locator('textarea').fill(dates.join('\n'));
  // 输出格式：Binary grid
  await page.locator('input[type="radio"]').nth(1).check();
  // 邮箱
  await page.locator('input[name="email"]').fill('15528366702@163.com');

  await page.screenshot({ path: path.join('D:/work/data/配套数据', `gacos_batch${batch}_filled.png`) });
  // 提交
  await page.getByRole('button', { name: 'Submit' }).click();
  await page.waitForURL(/result\.php/, { timeout: 60000 });
  console.log(`批 ${batch} 提交成功! URL:`, page.url().slice(0, 130));
  await browser.close();
  console.log('DONE');
})().catch(e => { console.error('FAIL:', e.message.split('\n')[0]); process.exit(1); });
