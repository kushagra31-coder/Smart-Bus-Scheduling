import pandas as pd
import matplotlib.pyplot as plt
import networkx as nx
import json
import numpy as np

def generate_transported_chart():
    df = pd.read_csv('results.csv')
    
    scenarios = df['Scenario']
    transported = df['Transported']
    stranded = df['Stranded']
    
    x = np.arange(len(scenarios))
    width = 0.35
    
    fig, ax = plt.subplots(figsize=(10, 6))
    ax.bar(x - width/2, transported, width, label='Transported', color='#2ecc71')
    ax.bar(x + width/2, stranded, width, label='Stranded', color='#e74c3c')
    
    ax.set_ylabel('Passengers')
    ax.set_title('Transported vs Stranded Passengers by Scheduler')
    ax.set_xticks(x)
    ax.set_xticklabels(scenarios)
    ax.legend()
    
    # Add labels on top of bars
    for i in range(len(scenarios)):
        ax.text(x[i] - width/2, transported[i] + 50, str(transported[i]), ha='center')
        ax.text(x[i] + width/2, stranded[i] + 50, str(stranded[i]), ha='center')
        
    plt.tight_layout()
    plt.savefig('transported_stranded.png', dpi=300)
    print("Saved transported_stranded.png")

def generate_runtime_chart():
    df = pd.read_csv('results.csv')
    
    scenarios = df['Scenario']
    runtimes = df['Runtime (s)']
    
    plt.figure(figsize=(8, 5))
    bars = plt.bar(scenarios, runtimes, color=['#95a5a6', '#3498db', '#9b59b6'])
    
    plt.ylabel('Execution Time (seconds)')
    plt.title('Algorithm Runtime Overhead')
    
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 0.01, f'{yval:.3f}s', ha='center', va='bottom')
        
    plt.tight_layout()
    plt.savefig('runtime_comparison.png', dpi=300)
    print("Saved runtime_comparison.png")

def generate_route_diagram():
    # Load a couple of routes to show shared junctions
    with open('data/routes.json', 'r') as f:
        routes_data = json.load(f)
        
    # Pick two routes that likely share a junction
    # e.g., M1 and M2, or something from the dataset
    r1 = routes_data[0] # Just take the first one
    r2 = routes_data[1] # And second one
    
    G = nx.Graph()
    # Add nodes and edges for R1
    r1_stops = r1['stopSequence']
    for i in range(len(r1_stops) - 1):
        G.add_edge(r1_stops[i], r1_stops[i+1], route=r1['routeId'])
        
    # Add nodes and edges for R2
    r2_stops = r2['stopSequence']
    for i in range(len(r2_stops) - 1):
        G.add_edge(r2_stops[i], r2_stops[i+1], route=r2['routeId'])
        
    # Find shared stops
    set1 = set(r1_stops)
    set2 = set(r2_stops)
    shared = set1.intersection(set2)
    
    pos = nx.spring_layout(G, seed=42)
    
    plt.figure(figsize=(12, 8))
    
    # Draw non-shared nodes
    non_shared = list(set(G.nodes()) - shared)
    nx.draw_networkx_nodes(G, pos, nodelist=non_shared, node_color='lightblue', node_size=300)
    
    # Draw shared nodes (junctions)
    if shared:
        nx.draw_networkx_nodes(G, pos, nodelist=list(shared), node_color='orange', node_size=600, label='Shared Junctions')
        
    # Draw edges
    edges_r1 = [(u, v) for u, v, d in G.edges(data=True) if d.get('route') == r1['routeId']]
    edges_r2 = [(u, v) for u, v, d in G.edges(data=True) if d.get('route') == r2['routeId']]
    
    nx.draw_networkx_edges(G, pos, edgelist=edges_r1, edge_color='blue', width=2, label=r1['routeId'])
    nx.draw_networkx_edges(G, pos, edgelist=edges_r2, edge_color='green', width=2, label=r2['routeId'])
    
    # Draw labels
    # only label shared nodes to avoid clutter
    labels = {node: node for node in shared}
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10, font_weight='bold')
    
    plt.title(f'Route Junction Analysis: {r1["routeId"]} and {r2["routeId"]}')
    plt.legend(['Shared Junctions', r1['routeId'], r2['routeId']])
    plt.axis('off')
    
    plt.tight_layout()
    plt.savefig('route_junctions.png', dpi=300)
    print("Saved route_junctions.png")

if __name__ == "__main__":
    generate_transported_chart()
    generate_runtime_chart()
    generate_route_diagram()
