import request from './index'

export function triggerSync(data) {
  return request({
    url: '/sync/trigger',
    method: 'post',
    data
  })
}

export function getSyncHistory(params) {
  return request({
    url: '/sync/history',
    method: 'get',
    params
  })
}

export function getSyncStatus(taskId) {
  return request({
    url: `/sync/status/${taskId}`,
    method: 'get'
  })
}
