/* Read-only client release preflight. Does not upload or contact the backend. */
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname,'..');
if (process.argv.includes('--help')) {
  console.log('node scripts/check_miniprogram_release.cjs [--config /absolute/path/to/client.config.cjs]\nChecks local client configuration only. No credentials, uploads or network calls.');
  process.exit(0);
}
const index=process.argv.indexOf('--config');
if(index>=0 && !process.argv[index+1]) { console.error('--config requires a path'); process.exit(2); }
const configPath=index>=0 ? path.resolve(process.argv[index+1]) : path.join(root,'miniprogram/config.js');
const config=require(configPath);
const project=JSON.parse(fs.readFileSync(path.join(root,'miniprogram/project.config.json'),'utf8'));
const privatePath=path.join(root,'miniprogram/project.private.config.json');
const privateProject=fs.existsSync(privatePath) ? JSON.parse(fs.readFileSync(privatePath,'utf8')) : {};
const effectiveUrlCheck=privateProject.setting?.urlCheck ?? project.setting?.urlCheck;
let origin;
try { origin=new URL(config.apiBase); } catch (_) {}
const hostname=origin && origin.hostname.toLowerCase();
const local=hostname && (hostname==='localhost' || hostname.endsWith('.localhost') || hostname.endsWith('.local') || hostname.includes(':') || /^[\d.]+$/.test(hostname));
const example=hostname && (hostname==='example.com' || hostname.endsWith('.example.com') || hostname.endsWith('.invalid') || hostname.endsWith('.test'));
const checks=[
  ['正式AppID匹配',project.appid==='wxcf1571f64e71f165'],
  ['关闭开发登录',config.developmentLogin===false],
  ['使用HTTPS公网接口域名',!!origin && origin.protocol==='https:' && !local && !example && hostname.includes('.')],
  ['接口地址无查询参数、片段或用户凭据',!!origin && !origin.search && !origin.hash && !origin.username && !origin.password],
  ['公共项目配置开启域名校验',project.setting.urlCheck===true],
  ['本机有效配置开启域名校验（含私有覆盖）',effectiveUrlCheck===true]
];
for(const [label,ok] of checks) console.log(`${ok ? 'PASS' : 'BLOCK'} ${label}`);
console.log('本检查不证明域名已备案、证书可用、微信域名白名单已配置或后端已通过生产验收。');
process.exitCode=checks.every(([,ok])=>ok) ? 0 : 1;
