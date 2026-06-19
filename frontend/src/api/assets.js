import request from './index'

export function getAssets(params) {
  return request({
    url: '/assets',
    method: 'get',
    params
  })
}

export function getAssetDetail(id) {
  return request({
    url: `/assets/${id}`,
    method: 'get'
  })
}

export function getAssetColumns(id) {
  return request({
    url: `/assets/${id}/columns`,
    method: 'get'
  })
}

export function getAssetPartitions(id) {
  return request({
    url: `/assets/${id}/partitions`,
    method: 'get'
  })
}

export function searchAssets(keyword) {
  return request({
    url: '/assets/search',
    method: 'get',
    params: { keyword }
  })
}
