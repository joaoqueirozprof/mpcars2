import axios, { AxiosInstance, AxiosError } from 'axios'

const getApiBaseUrl = (): string => {
  const hostname = window.location.hostname
  if (hostname === 'localhost' || hostname === '127.0.0.1') {
    return '/api/v1'
  }
  // In production, connect directly to API port
  return `http://${hostname}:8002/api/v1`
}

const api: AxiosInstance = axios.create({
  baseURL: getApiBaseUrl(),
  headers: {
    'Content-Type': 'application/json',
  },
})

api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error: AxiosError) => {
    return Promise.reject(error)
  }
)

let _isRedirecting = false

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && !_isRedirecting) {
      const currentPath = window.location.pathname
      if (currentPath !== '/login') {
        _isRedirecting = true
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        setTimeout(() => { window.location.href = '/login' }, 100)
      }
    }
    return Promise.reject(error)
  }
)

export default api
