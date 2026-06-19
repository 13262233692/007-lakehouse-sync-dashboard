import axios from 'axios'
import { ElMessage } from 'element-plus'
import { useAppStore } from '@/store'

const service = axios.create({
  baseURL: '/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

service.interceptors.request.use(
  (config) => {
    const appStore = useAppStore()
    appStore.setLoading(true)
    return config
  },
  (error) => {
    const appStore = useAppStore()
    appStore.setLoading(false)
    return Promise.reject(error)
  }
)

service.interceptors.response.use(
  (response) => {
    const appStore = useAppStore()
    appStore.setLoading(false)
    const res = response.data
    if (res.code && res.code !== 0 && res.code !== 200) {
      ElMessage.error(res.message || '请求失败')
      return Promise.reject(new Error(res.message || '请求失败'))
    }
    return res
  },
  (error) => {
    const appStore = useAppStore()
    appStore.setLoading(false)
    const message = error.response?.data?.message || error.message || '网络错误'
    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default service
