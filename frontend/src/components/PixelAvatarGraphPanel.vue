<template>
  <div class="graph-panel">
    <div class="graph-container" ref="graphContainer">
      <svg ref="graphSvg" class="graph-svg"></svg>
      <div v-if="selectedItem" class="detail-panel">
        <div class="detail-header">
          <span>{{ selectedItem.type === 'node' ? 'Agent Info' : 'Interaction' }}</span>
          <button @click="selectedItem = null">×</button>
        </div>
        <div class="detail-content">
          <div v-if="selectedItem.type === 'node'">
            <p><b>Name:</b> {{ selectedItem.data.name }}</p>
            <p><b>Type:</b> {{ selectedItem.data.labels?.[0] }}</p>
            <p v-if="selectedItem.data.summary"><b>Summary:</b> {{ selectedItem.data.summary }}</p>
          </div>
          <div v-else>
            <p>{{ selectedItem.data.source_name }} → {{ selectedItem.data.name }} → {{ selectedItem.data.target_name }}</p>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, nextTick, onMounted } from 'vue'
import * as d3 from 'd3'

const props = defineProps({ graphData: Object })
const graphContainer = ref(null)
const graphSvg = ref(null)
const selectedItem = ref(null)
let simulation = null

// 生成像素小人SVG
const getPixelAvatar = (type, influence = 1) => {
  const size = Math.min(28, 16 + (influence - 1) * 6)
  const colors = {
    'Official': '#1A535C', 'University': '#4F759B', 'MediaOutlet': '#E74C3C',
    'Professor': '#8E44AD', 'Student': '#F39C12', 'Person': '#95A5A6'
  }
  const color = colors[type] || '#9B59B6'
  return `
    <svg width="${size}" height="${size}" viewBox="0 0 16 20">
      <rect x="5" y="12" width="6" height="8" fill="${color}" />
      <rect x="4" y="13" width="2" height="5" fill="${color}" />
      <rect x="10" y="13" width="2" height="5" fill="${color}" />
      <rect x="4" y="2" width="8" height="10" fill="#FFDBAC" rx="1" />
      <rect x="6" y="5" width="1" height="1" fill="#000" />
      <rect x="9" y="5" width="1" height="1" fill="#000" />
      <rect x="6.5" y="8" width="3" height="1" fill="#000" />
      <rect x="4" y="2" width="8" height="2" fill="#2C2C2C" />
    </svg>
  `
}

const render = () => {
  if (!graphSvg.value || !props.graphData) return
  if (simulation) simulation.stop()
  
  const w = graphContainer.value.clientWidth
  const h = graphContainer.value.clientHeight
  const svg = d3.select(graphSvg.value).attr('width', w).attr('height', h)
  svg.selectAll('*').remove()
  
  const nodes = (props.graphData.nodes || []).map(n => ({
    id: n.uuid, name: n.name, type: n.labels?.[0] || 'Entity',
    influence: n.attributes?.influence_weight || 1, raw: n
  }))
  const edges = (props.graphData.edges || []).map(e => ({
    source: e.source_node_uuid, target: e.target_node_uuid, raw: e
  }))
  
  const g = svg.append('g')
  svg.call(d3.zoom().on('zoom', e => g.attr('transform', e.transform)))
  
  // 连线
  g.append('g').selectAll('line')
    .data(edges)
    .enter().append('line')
    .attr('stroke', '#ccc')
    .attr('stroke-width', 1.5)
  
  // 像素小人节点
  const node = g.append('g').selectAll('g')
    .data(nodes)
    .enter().append('g')
    .style('cursor', 'pointer')
    .call(d3.drag().on('drag', (e, d) => { d.fx = e.x; d.fy = e.y }))
    .on('click', (e, d) => {
      e.stopPropagation()
      selectedItem.value = { type: 'node', data: d.raw }
    })
    .html(d => getPixelAvatar(d.type, d.influence))
  
  // 标签
  g.append('g').selectAll('text')
    .data(nodes)
    .enter().append('text')
    .text(d => d.name.length > 6 ? d.name.slice(0,6)+'…' : d.name)
    .attr('font-size', '10px')
    .attr('text-anchor', 'middle')
    .attr('dy', 25)
  
  // 力导向布局
  simulation = d3.forceSimulation(nodes)
    .force('link', d3.forceLink(edges).id(d => d.id).distance(120))
    .force('charge', d3.forceManyBody().strength(-300))
    .force('center', d3.forceCenter(w/2, h/2))
    .force('collide', d3.forceCollide(30))
    .on('tick', () => {
      g.selectAll('line')
        .attr('x1', d => d.source.x)
        .attr('y1', d => d.source.y)
        .attr('x2', d => d.target.x)
        .attr('y2', d => d.target.y)
      node.attr('transform', d => `translate(${d.x-8}, ${d.y-10})`)
      g.selectAll('text').attr('x', d => d.x).attr('y', d => d.y)
    })
}

watch(() => props.graphData, () => nextTick(render), { deep: true })
onMounted(() => nextTick(render))
</script>

<style scoped>
.graph-panel { width: 100%; height: 100%; background: #fafafa; position: relative; }
.graph-container { width: 100%; height: 100%; }
.graph-svg { width: 100%; height: 100%; }
.detail-panel {
  position: absolute; top: 20px; right: 20px; width: 280px;
  background: #fff; border-radius: 8px; padding: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.1); z-index: 10;
}
.detail-header {
  display: flex; justify-content: space-between;
  font-weight: 600; margin-bottom: 10px;
}
.detail-header button { border: none; background: none; cursor: pointer; font-size: 18px; }
</style>