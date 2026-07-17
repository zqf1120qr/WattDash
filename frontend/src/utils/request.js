import axios from 'axios'
import { ElMessage } from 'element-plus'

const service = axios.create({
  baseURL: '/api/v1',
  timeout: 60000 // 60 seconds (useful for Chromium startup which takes time)
})

// Request interceptor
service.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor
service.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const status = error.response ? error.response.status : null
    
    if (status === 401) {
      localStorage.removeItem('token')
      // Let App.vue handle state reset via event or reload
      window.dispatchEvent(new Event('auth-expired'))
      ElMessage.error('登录会话已过期，请重新登录')
    } else {
      const msg = error.response && error.response.data && error.response.data.detail 
        ? error.response.data.detail 
        : '网络请求错误，请稍后重试'
      ElMessage.error(msg)
    }
    return Promise.reject(error)
  }
)

export default service
