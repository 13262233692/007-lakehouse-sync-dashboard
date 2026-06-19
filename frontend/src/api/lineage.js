import request from '@/api/index'

export const getLineageForceGraph = (forceRefresh = false) => {
  return request({
    url: '/lineage/force-graph',
    method: 'get',
    params: { force_refresh: forceRefresh }
  })
}

export const getLineageDag = (forceRefresh = false) => {
  return request({
    url: '/lineage/dag',
    method: 'get',
    params: { force_refresh: forceRefresh }
  })
}

export const getLineageDelays = (forceRefresh = false) => {
  return request({
    url: '/lineage/refresh-delays',
    method: 'get',
    params: { force_refresh: forceRefresh }
  })
}

export const getLineageNode = (nodeFqn, depth = 3) => {
  return request({
    url: `/lineage/node/${encodeURIComponent(nodeFqn)}`,
    method: 'get',
    params: { depth }
  })
}
