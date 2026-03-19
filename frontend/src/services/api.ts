import axios, { AxiosInstance, AxiosError } from 'axios'

const api: AxiosInstance = axios.create({
  baseURL: '/api/v1',
  headers: {
    'Content-Type': 'application/json',
  },
  // CRITICAL: prevent axios from following redirects that break CORS
  maxRedirects: 0,
  validateStatus: (status) => status < 400 || status === 307,
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

// Handle 307 redirects manually - fix the URL to stay on the same origin
api.interceptors.response.use(
  (response) => {
    if (response.status === 307 && response.headers.location) {
      const location = response.headers.location as string
      // Convert absolute redirect URL to relative path
      let redirectPath = location
      try {
        const url = new URL(location)
        redirectPath = url.pathname + url.search
      } catch {
        // already relative
      }
      // Retry the request with the corrected URL
      return api.request({
        ...response.config,
        url: redirectPath,
        baseURL: '',
        maxRedirects: 0,
      })
    }
    return response
  },
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      const currentPath = window.location.pathname
      if (currentPath !== '/login') {
        localStorage.removeItem('access_token')
        localStorage.removeItem('user')
        setTimeout(() => { window.location.href = '/login' }, 100)
      }
    }
    return Promise.reject(error)
  }
)

export default api
