const api = require('./utils/api');
App({ onLaunch() { api.validateConfig(); } });
