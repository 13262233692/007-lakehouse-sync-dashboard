import request from './index'

export function getOverview() {
  return request({
    url: '/stats/overview',
    method: 'get'
  })
}

export function getTreeData(params) {
  return request({
    url: '/stats/tree',
    method: 'get',
    params
  })
}

export function getTrendData(params) {
  return request({
    url: '/stats/trend',
    method: 'get',
    params
  })
}

export function getSourceBreakdown() {
  return request({
    url: '/stats/source-breakdown',
    method: 'get'
  })
}
