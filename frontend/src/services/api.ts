import axios, { AxiosInstance, AxiosError } from 'axios'

const getApiBaseUrl = (): string => {
  return '/api/v1'
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
