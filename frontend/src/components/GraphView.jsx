import React, { useEffect, useRef, useState } from 'react';
import * as d3 from 'd3';

export default function GraphView({ graph, onNodeClick }) {
  const ref = useRef(null);
  const [selectedNodeId, setSelectedNodeId] = useState(null);
  const simulationRef = useRef(null);

  useEffect(() => {
    const container = ref.current;
    if (!container || !graph.nodes || graph.nodes.length === 0) return;
    
    // Only clear and rebuild if graph structure actually changed
    container.innerHTML = '';

    const width = container.clientWidth || 800;
    const height = container.clientHeight || 600;

    const svg = d3.select(container).append('svg')
      .attr('width', width)
      .attr('height', height)
      .style('background', 'transparent');

    // Add zoom behavior
    const g = svg.append('g');
    
    const zoom = d3.zoom()
      .scaleExtent([0.2, 4])
      .on('zoom', (event) => {
        g.attr('transform', event.transform);
      });
    
    svg.call(zoom);

    const color = (d) => d.type === 'paper' ? '#60a5fa' : '#34d399';

    // Enhanced force simulation with better spacing
    const sim = d3.forceSimulation(graph.nodes)
      .force('link', d3.forceLink(graph.edges).id(d => d.id).distance(d => 80 + 20 * (1/Math.max(0.1, d.weight || 1))))
      .force('charge', d3.forceManyBody().strength(-400).distanceMax(400))
      .force('center', d3.forceCenter(width/2, height/2))
      .force('collision', d3.forceCollide().radius(30))
      .alphaDecay(0.02);

    // Links with glow effect
    const link = g.append('g').selectAll('line')
      .data(graph.edges)
      .enter().append('line')
      .attr('stroke', '#334155')
      .attr('stroke-opacity', 0.25)
      .attr('stroke-width', d => 1.5 + Math.log1p(d.weight || 1) * 0.5)
      .attr('class', 'graph-link')
      .attr('stroke-linecap', 'round');

    // Larger nodes with smooth animations
    const node = g.append('g').selectAll('circle')
      .data(graph.nodes)
      .enter().append('circle')
      .attr('r', d => d.type === 'paper' ? 12 : 8)
      .attr('fill', color)
      .attr('stroke', '#0a0f1e')
      .attr('stroke-width', 2)
      .attr('class', 'graph-node')
      .call(d3.drag()
        .on('start', (event, d) => { if (!event.active) sim.alphaTarget(0.3).restart(); d.fx = d.x; d.fy = d.y; })
        .on('drag', (event, d) => { d.fx = event.x; d.fy = event.y; })
        .on('end', (event, d) => { if (!event.active) sim.alphaTarget(0); d.fx = null; d.fy = null; })
      )
      .style('cursor', 'pointer')
      .on('click', (event, d) => {
        setSelectedNodeId(d.id);
        
        // Smooth transition for selected node
        node.transition().duration(300)
            .attr('stroke-width', n => n.id === d.id ? 4 : 2)
            .attr('stroke', n => n.id === d.id ? '#fbbf24' : '#0a0f1e')
            .attr('r', n => {
              if (n.id === d.id) return n.type === 'paper' ? 16 : 12;
              return n.type === 'paper' ? 12 : 8;
            });
        
        // Find neighbor IDs
        const neighborIds = new Set();
        graph.edges.forEach(e => {
          if (e.source.id === d.id) neighborIds.add(e.target.id);
          if (e.target.id === d.id) neighborIds.add(e.source.id);
        });

        // Smooth transition for edges with glow
        link.transition().duration(300)
            .attr('stroke', e => 
              (e.source.id === d.id || e.target.id === d.id) ? '#60a5fa' : '#334155'
            )
            .attr('stroke-opacity', e => 
              (e.source.id === d.id || e.target.id === d.id) ? 0.8 : 0.15
            )
            .attr('stroke-width', e => 
              (e.source.id === d.id || e.target.id === d.id) 
                ? 3 + Math.log1p(e.weight || 1) 
                : 1.5 + Math.log1p(e.weight || 1) * 0.5
            )
            .attr('class', e => 
              (e.source.id === d.id || e.target.id === d.id) ? 'graph-link highlighted' : 'graph-link'
            );

        // Smooth fade for non-selected nodes
        node.transition().duration(300)
            .style('opacity', n => {
              if (n.id === d.id || neighborIds.has(n.id)) return 1;
              return 0.25;
            });

        // Smooth fade for labels
        label.transition().duration(300)
            .style('opacity', n => {
              if (n.id === d.id || neighborIds.has(n.id)) return 1;
              return 0.15;
            })
            .attr('font-size', n => n.id === d.id ? 12 : 10)
            .attr('font-weight', n => n.id === d.id ? 700 : 400);

        onNodeClick && onNodeClick(d, event);
      });

    const label = g.append('g').selectAll('text')
      .data(graph.nodes)
      .enter().append('text')
      .text(d => d.label)
      .attr('font-size', 10)
      .attr('dx', 14)
      .attr('dy', 5)
      .attr('fill', '#94a3b8')
      .attr('class', 'graph-label')
      .style('pointer-events', 'none')
      .style('user-select', 'none');

    sim.on('tick', () => {
      link.attr('x1', d => d.source.x)
          .attr('y1', d => d.source.y)
          .attr('x2', d => d.target.x)
          .attr('y2', d => d.target.y);

      node.attr('cx', d => d.x).attr('cy', d => d.y);

      label.attr('x', d => d.x).attr('y', d => d.y);
    });

    simulationRef.current = sim;

    // Cleanup
    return () => {
      if (simulationRef.current) {
        simulationRef.current.stop();
      }
    };
  }, [graph.nodes.length, graph.edges.length]); // Only re-render when graph size changes

  return <div ref={ref} style={{ width: '100%', height: '100%' }} />;
}