# Project Diagrams Index

This directory contains all project diagrams organized by category. Each diagram is a self-contained HTML file with inline SVG, generated using the Diagram Design skill.

## Directory Structure

```
docs/diagram/
├── Structural Diagrams (01-10)
├── Behavioral Diagrams (11-20)
├── Functional/Data Diagrams (21-27)
├── Technical/Chart Diagrams (28-40)
└── Specialized Diagrams (41-44)
```

---

## 1. Structural Diagrams (Architecture & Organization)

| # | File | Description | Type |
|---|------|-------------|------|
| 01 | `01-structural-architecture.html` | System architecture with components, connections, and zones | Architecture |
| 02 | `02-structural-high-level.html` | End-to-end data stack on container cluster | High-Level |
| 03 | `03-structural-layer-stack.html` | Stacked abstraction levels | Layer Stack |
| 04 | `04-structural-nested.html` | Hierarchy through containment/scope | Nested |
| 05 | `05-structural-tree.html` | Parent → children relationships | Tree |
| 06 | `06-structural-org-chart.html` | Human/agent/team ownership, reporting, routing | Org Chart |
| 07 | `07-structural-dependency-graph.html` | What depends on what, with fan-in and cycles | Dependency Graph |
| 08 | `08-structural-deployment.html` | Where software runs — zones, hosts, artifacts, replicas, ports | Deployment |
| 09 | `09-structural-database-schema.html` | Physical tables: SQL types, constraints, indexes, FKs | Database Schema |
| 10 | `10-structural-uml-class.html` | Classes with operations, inheritance, composition | UML Class |

**Use cases**: System design docs, architecture decision records, onboarding, infrastructure planning

---

## 2. Behavioral Diagrams (Process & Interaction)

| # | File | Description | Type |
|---|------|-------------|------|
| 11 | `11-behavioral-flowchart.html` | Decision logic with branches | Flowchart |
| 12 | `12-behavioral-sequence.html` | Time-ordered messages between actors | Sequence |
| 13 | `13-behavioral-state-machine.html` | States + transitions + guards | State Machine |
| 14 | `14-behavioral-process.html` | Multi-actor sequential process with data handoffs | Process |
| 15 | `15-behavioral-swimlane.html` | Cross-functional process with handoffs | Swimlane |
| 16 | `16-behavioral-timeline.html` | Events positioned in time | Timeline |
| 17 | `17-behavioral-gantt.html` | Tasks and phases on a timeline | Gantt |
| 18 | `18-behavioral-user-journey.html` | What a person does across stages, and how it feels | User Journey |
| 19 | `19-behavioral-service-blueprint.html` | Customer actions vs service internals, line of visibility | Service Blueprint |
| 20 | `20-behavioral-kanban.html` | Work-in-progress by state, WIP limits, blocked items | Kanban |

**Use cases**: Requirements analysis, user story mapping, process documentation, sprint planning

---

## 3. Functional/Data Diagrams (Data Flow & Models)

| # | File | Description | Type |
|---|------|-------------|------|
| 21 | `21-functional-data-flow.html` | Role-scoped data flow: who does what at each step | Data Flow |
| 22 | `22-functional-er-model.html` | Entities + fields + relationships | ER / Data Model |
| 23 | `23-functional-sankey.html` | Quantity splitting/merging across stages | Sankey |
| 24 | `24-functional-medallion.html` | Multi-tier data storage with quality levels | Medallion |
| 25 | `25-functional-dp-integration.html` | Integration topology: sources → core → consumers | DP Integration |
| 26 | `26-functional-dp-security-matrix.html` | Per-role/per-component access permissions | DP Security Matrix |
| 27 | `27-functional-story-map.html` | Narrative backbone sliced into releases | Story Map |

**Use cases**: Data architecture, ETL pipeline design, access control docs, product planning

---

## 4. Technical/Chart Diagrams (Quantitative & Analytical)

| # | File | Description | Type |
|---|------|-------------|------|
| 28 | `28-technical-bar-chart.html` | Quantitative comparison across categories | Bar Chart |
| 29 | `29-technical-line-chart.html` | Continuous trends over time, slopegraph, ridgeline, bump | Line Chart |
| 30 | `30-technical-scatter-plot.html` | Correlation/distribution of two variables | Scatter Plot |
| 31 | `31-technical-heatmap.html` | Cross-tabulated data; fill encodes value | Heatmap |
| 32 | `32-technical-treemap.html` | Part-of-whole where relative sizes are the story | Treemap |
| 33 | `33-technical-radar-chart.html` | Multiple entities scored across 3-5 criteria | Radar / Spider |
| 34 | `34-technical-polar-chart.html` | One series across cyclic categories | Polar Chart |
| 35 | `35-technical-quadrant.html` | Two-axis positioning / prioritization | Quadrant |
| 36 | `36-technical-waterfall.html` | Start total bridged to end total by signed contributions | Waterfall |
| 37 | `37-technical-pyramid-funnel.html` | Ranked hierarchy or conversion drop-off | Pyramid / Funnel |
| 38 | `38-technical-venn.html` | Overlap between sets | Venn |
| 39 | `39-technical-fishbone.html` | Causes of observed effect, grouped by category | Fishbone |
| 40 | `40-technical-wardley-map.html` | Value chain against evolution | Wardley Map |

**Use cases**: Metrics dashboards, performance analysis, root cause analysis, strategic planning

---

## 5. Specialized Diagrams (Unique Visualizations)

| # | File | Description | Type |
|---|------|-------------|------|
| 41 | `41-specialized-exploded.html` | Parts pulled apart along one axis: teardown, assembly | Exploded Axonometric |
| 42 | `42-specialized-axonometric-plan.html` | One floor/site seen from above at an angle | Axonometric Plan |
| 43 | `43-specialized-it-current-state.html` | Legacy IT landscape by phase/department | IT Current-State |
| 44 | `44-specialized-loop-flywheel.html` | Reinforcing cycle; last step feeds first | Loop / Flywheel |

**Use cases**: Hardware documentation, facility planning, legacy modernization, growth loops

---

## Diagram Categories Summary

| Category | Count | Diagram Numbers | Primary Use |
|----------|-------|-----------------|-------------|
| **Structural** | 10 | 01-10 | Architecture, deployment, data models |
| **Behavioral** | 10 | 11-20 | Processes, interactions, user flows |
| **Functional/Data** | 7 | 21-27 | Data pipelines, integrations, security |
| **Technical/Charts** | 13 | 28-40 | Metrics, analytics, quantitative analysis |
| **Specialized** | 4 | 41-44 | Hardware, facilities, legacy, growth |
| **Total** | **44** | | |

---

## How to Use These Diagrams

### Viewing
Open any `.html` file directly in a browser. They are self-contained with embedded CSS and inline SVG.

### Exporting to SVG/PNG
From the diagram-design skill directory:
```bash
# Export to SVG
python3 scripts/export_svg.py docs/diagram/01-structural-architecture.html output.svg

# Export to PNG (requires Playwright)
python3 scripts/export_png.py docs/diagram/01-structural-architecture.html output.png
```

### Customizing
Each diagram follows the Diagram Design skill's design system. To customize branding:
1. Edit `.agents/skills/diagram-design/references/style-guide.md` with your brand tokens
2. Or run the onboarding flow (see `references/onboarding.md`)

### Importing Existing Diagrams
Convert draw.io, Mermaid, or Excalidraw files:
```bash
# Mermaid
python3 scripts/mermaid_extract.py input.mmd

# draw.io
python3 scripts/drawio_extract.py input.drawio

# Excalidraw
python3 scripts/excalidraw_extract.py input.excalidraw
```

Then redraw using the extracted IR and the appropriate type reference.

---

## Quality Standards (Taste Gate)

All diagrams in this directory pass the Pre-Output Checklist (§9 of SKILL.md):
- ✅ Complexity budget respected (max 9 nodes, 12 arrows, 2 coral elements)
- ✅ Orthogonal connectors only (r=8 elbows)
- ✅ Label masks with 6-10px gap from stroke
- ✅ No overlapping connectors
- ✅ Accessible SVG (role="img", aria-labelledby, proper title/desc)
- ✅ Single self-contained HTML file
- ✅ Coral used on ≤2 focal elements
- ✅ Legend covers every type used

---

## Regenerating Diagrams

To regenerate or create new diagrams, use the Diagram Designer agent:

```bash
# Start the CLI
uv run python -m src.cli

# In the CLI, the diagram-designer agent is available
# Use /agents show diagram-designer to see details
# Or give it a task like: "Create an architecture diagram for our microservices platform"
```

The agent will:
1. Check if style guide needs customization (first run only)
2. Select appropriate visual type and semantic pattern
3. Load the matching type reference
4. Create the diagram following all design rules
5. Run the taste gate before delivering

---

*Generated on 2026-11-09 using Diagram Design skill v2.6*