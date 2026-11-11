---
name: diagram
description: "Skill for creating and finalizing diagrams including technical fundamentals, data flow, API layer integration, and other diagram types"
license: MIT
compatibility: Python 3.11+
metadata:
  version: "1.0"
  skill-author: User
  categories:
    - diagramming
    - visualization
    - technical-documentation
---

# diagram

## When to use

Use this skill when:
- You need to create or finalize technical diagrams
- You need to generate diagram code for various diagram types
- You want to visualize system architecture, data flows, or API integrations
- You need to export diagrams in multiple formats (Mermaid, PlantUML, GraphViz)

Trigger conditions:
- User requests diagram creation or finalization
- Technical documentation needs visual representation
- Architecture review requires diagrams

## Workflow

1. **Understand Requirements**
   - Identify diagram type needed
   - Gather components, relationships, and constraints
   - Determine output format preference

2. **Select Diagram Type**
   - Technical Fundamentals: Component, class, sequence diagrams
   - Data Flow: DFD, flowcharts, pipeline diagrams
   - API Layer Integration: API gateway, service mesh, endpoint maps
   - Additional Types: Network, deployment, ER diagrams

3. **Generate Diagram**
   - Create diagram structure
   - Apply styling and layout
   - Validate syntax

4. **Finalize & Export**
   - Render to target format
   - Provide editable source
   - Generate multiple format options

## Diagram Types Supported

### Technical Fundamentals
- **Component Diagrams**: System components and interfaces
- **Class Diagrams**: Object-oriented structure
- **Sequence Diagrams**: Interaction flows over time
- **State Diagrams**: State transitions

### Data Flow Diagrams
- **Context Diagrams**: System boundaries and external entities
- **Level 0-2 DFDs**: Progressive decomposition
- **Flowcharts**: Process logic and decision points
- **Pipeline Diagrams**: Data transformation stages

### API Layer Integration
- **API Gateway Diagrams**: Routing, auth, rate limiting
- **Service Mesh**: Sidecars, control plane, observability
- **Endpoint Maps**: REST/GraphQL/gRPC endpoints
- **Contract Diagrams**: Request/response schemas

### Additional Types
- **Network Diagrams**: Topology, zones, connectivity
- **Deployment Diagrams**: Nodes, artifacts, environments
- **ER Diagrams**: Entities, relationships, attributes
- **C4 Model**: Context, Container, Component, Code

## Tools required

- read_file: Read diagram specifications
- write_file: Write diagram source files
- bash: Run diagram rendering tools
- glob: Find existing diagram files

## Inputs/Outputs

### Inputs
| Parameter | Type | Description |
|-----------|------|-------------|
| diagram_type | string | Type: "technical", "dataflow", "api", "network", "deployment", "er", "c4" |
| sub_type | string | Specific subtype (e.g., "sequence", "component", "context") |
| specification | object | Diagram specification with nodes, edges, styling |
| output_format | string | "mermaid", "plantuml", "graphviz", "all" |
| output_path | string | Output file path (optional) |

### Outputs
| Output | Type | Description |
|--------|------|-------------|
| diagram_source | string | Diagram source code in requested format |
| rendered_path | string | Path to rendered output (if rendered) |
| formats | list[string] | Available output formats |
| validation | object | Syntax validation results |

## Scripts

- generate_diagram.py: Main diagram generation script
- render_diagram.py: Diagram rendering utilities
- templates/: Diagram templates for each type

## Assets

- templates/technical/*.mmd: Technical diagram templates
- templates/dataflow/*.mmd: Data flow diagram templates
- templates/api/*.mmd: API integration templates
- templates/network/*.mmd: Network diagram templates
- templates/deployment/*.mmd: Deployment templates
- templates/er/*.mmd: ER diagram templates
- templates/c4/*.mmd: C4 model templates