const config = require('../config');
let loginPromise;
function validateConfig() {
  const version = wx.getAccountInfoSync().miniProgram.envVersion;
  if (version !== 'develop' && (config.developmentLogin || !config.apiBase.startsWith('https://'))) {
    throw new Error('发布配置错误：必须关闭开发登录并配置 HTTPS');
  }
}
function raw(path, method, data, token) {
  return new Promise((resolve, reject) => wx.request({
    url: config.apiBase + '/mini' + path, method, data, timeout: 30000,
    header: token ? { Authorization: 'Bearer ' + token } : {},
    success(res) {
      if (res.statusCode >= 200 && res.statusCode < 300) return resolve(res.data);
      const detail = res.data && res.data.detail;
      const err = new Error(typeof detail === 'string' ? detail : '请求失败，请稍后重试');
      err.status = res.statusCode; reject(err);
    },
    fail() { reject(new Error('无法连接服务，请检查网络后重试')); }
  }));
}
function login() {
  if (loginPromise) return loginPromise;
  loginPromise = (async () => {
    validateConfig();
    let code;
    if (config.developmentLogin) {
      let identity = wx.getStorageSync('miniDevIdentity');
      if (!identity) {
        identity = Date.now().toString(36) + Math.random().toString(36).slice(2) + Math.random().toString(36).slice(2);
        wx.setStorageSync('miniDevIdentity', identity);
      }
      code = 'dev:' + identity;
    } else {
      code = await new Promise((resolve, reject) => wx.login({
        success(result) { result.code ? resolve(result.code) : reject(new Error('微信登录失败')); },
        fail() { reject(new Error('微信登录失败，请重试')); }
      }));
    }
    const session = await raw('/login', 'POST', { code });
    wx.setStorageSync('miniSession', session);
    return session;
  })().finally(() => { loginPromise = null; });
  return loginPromise;
}
async function session() { return wx.getStorageSync('miniSession') || login(); }
async function request(path, method = 'GET', data, retried = false) {
  validateConfig();
  const auth = await session();
  try { return await raw(path, method, data, auth.token); }
  catch (error) {
    if (error.status === 401 && !retried) {
      wx.removeStorageSync('miniSession'); await login();
      return request(path, method, data, true);
    }
    throw error;
  }
}
async function download(id, retried = false) {
  validateConfig();
  const auth = await session();
  const result = await new Promise((resolve, reject) => wx.downloadFile({
    url: config.apiBase + '/mini/tasks/' + encodeURIComponent(id) + '/export',
    header: { Authorization: 'Bearer ' + auth.token },
    success: resolve, fail() { reject(new Error('文件下载失败，请重试')); }
  }));
  if (result.statusCode === 401 && !retried) {
    wx.removeStorageSync('miniSession'); await login(); return download(id, true);
  }
  if (result.statusCode !== 200) throw new Error('文字尚未就绪，或文件已删除');
  return result.tempFilePath;
}
module.exports = { request, session, download, validateConfig };
