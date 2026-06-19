import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useAppStore = defineStore('app', () => {
  const loading = ref(false)

  function setLoading(value) {
    loading.value = value
  }

  return {
    loading,
    setLoading
  }
})

export const useAssetStore = defineStore('asset', () => {
  const searchResults = ref([])
  const searchKeyword = ref('')
  const selectedAsset = ref(null)

  const hasSearchResults = computed(() => searchResults.value.length > 0)

  function setSearchResults(results, keyword) {
    searchResults.value = results
    searchKeyword.value = keyword
  }

  function clearSearchResults() {
    searchResults.value = []
    searchKeyword.value = ''
  }

  function setSelectedAsset(asset) {
    selectedAsset.value = asset
  }

  return {
    searchResults,
    searchKeyword,
    selectedAsset,
    hasSearchResults,
    setSearchResults,
    clearSearchResults,
    setSelectedAsset
  }
})
