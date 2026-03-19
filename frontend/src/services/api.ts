import axios, { AxiosInstance, AxiosError } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api/v1',
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
    // Ensure trailing slash ONLY on GET/DELETE to prevent FastAPI 307 redirects
    // POST/PUT/PATCH must NOT have trailing slash (307 redirect loses request body)
    const method = (config.method || 'get').toUpperCase()
    if (method === 'GET' || method === 'DELETE') {
      if (config.url) {
        const hasQuery = config.url.includes('?')
        if (hasQuery) {
          const idx = config.url.indexOf('?')
          const path = config.url.substring(0, idx)
          const query = config.url.substring(idx)
          if (!path.endsWith('/')) {
            config.url = path + '/' + query
          }
        } else if (!config.url.endsWith('/')) {
          config.url = config.url + '/'
        }
      }
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
