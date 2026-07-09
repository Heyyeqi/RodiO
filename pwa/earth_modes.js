(function () {
  const EARTH_MODES = {
    RAW: {
      tileSource: '/assets/earth/bmng21k/topo_bathy/tiles/',
      pipeline: 'raw',
      allowFallback: false,
      cachePrefix: 'raw',
    },

    NOON_AIR: {
      tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_noon_air/',
      pipeline: 'noon_air_full',
      allowFallback: false,
      cachePrefix: 'noon_air',
    },

    V2_ENHANCED: {
      tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_v2_enhanced/',
      pipeline: 'v2_global_baseline',
      allowFallback: false,
      cachePrefix: 'v2',
    },

    NOON_AIR_V2: {
      tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_noon_air_v2/',
      pipeline: 'noon_air_v2_final',
      allowFallback: false,
      cachePrefix: 'nav2',
    },

    NOON_AIR_V2_ISLANDS: {
      tileSource: '/assets/earth/bmng21k/topo_bathy/tiles_noon_air_v2_islands/',
      pipeline: 'noon_air_v2_island_pass',
      allowFallback: false,
      cachePrefix: 'nav2i',
    },
  }

  window.EARTH_MODES = EARTH_MODES
})()
