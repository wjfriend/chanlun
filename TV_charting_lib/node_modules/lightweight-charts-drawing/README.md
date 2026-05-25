# lightweight-charts-drawing

**[Live Demo](https://deepentropy.github.io/lightweight-charts-drawing/)**

68 drawing tools for TradingView's lightweight-charts library. Includes trend lines, Fibonacci tools, Gann analysis, channels, pitchforks, shapes, annotations, and forecasting tools.

## Installation

```bash
npm install lightweight-charts-drawing lightweight-charts
```

## Quick Start

```typescript
import { createChart, CandlestickSeries } from 'lightweight-charts';
import { DrawingManager, TrendLine, FibRetracement } from 'lightweight-charts-drawing';

// Create chart
const chart = createChart(document.getElementById('chart')!, {
  width: 800,
  height: 400,
});

const series = chart.addSeries(CandlestickSeries);
series.setData([/* ... your OHLC data ... */]);

// Set up drawing manager
const manager = new DrawingManager();
manager.attach(chart, series, document.getElementById('chart')!);

// Add a trend line
const trendLine = new TrendLine('tl-1', [
  { time: '2024-01-15', price: 100 },
  { time: '2024-02-15', price: 110 },
], { lineColor: '#2962FF', lineWidth: 2 });

manager.addDrawing(trendLine);

// Add a Fibonacci retracement
const fib = new FibRetracement('fib-1', [
  { time: '2024-01-01', price: 95 },
  { time: '2024-03-01', price: 115 },
]);

manager.addDrawing(fib);
```

## Lightweight-Charts Integration Example

```typescript
import { createChart, CandlestickSeries, ColorType } from 'lightweight-charts';
import {
  DrawingManager,
  TrendLine,
  HorizontalLine,
  Rectangle,
  TextAnnotation,
  getToolRegistry,
} from 'lightweight-charts-drawing';

// Create chart
const container = document.getElementById('chart')!;
const chart = createChart(container, {
  layout: {
    background: { type: ColorType.Solid, color: '#131722' },
    textColor: '#d1d4dc',
  },
  width: 1000,
  height: 500,
});

const series = chart.addSeries(CandlestickSeries);
series.setData([/* ... OHLC data ... */]);

// Initialize drawing manager
const manager = new DrawingManager();
manager.attach(chart, series, container);

// Listen for events
manager.on('drawing:selected', (event) => {
  console.log('Selected:', event.drawingId);
});

// Add drawings programmatically
const support = new HorizontalLine('support', [
  { time: '2024-01-01' as any, price: 95 },
], { lineColor: '#26a69a', lineWidth: 1 });

manager.addDrawing(support);

// Select, deselect, remove
manager.selectDrawing('support');
manager.deselectAll();
manager.removeDrawing('support');

// Export/import drawings as JSON
const json = manager.exportDrawings();
// manager.importDrawings(json, factory);

// Access the tool registry for all 68 tool definitions
const registry = getToolRegistry();
const allTools = registry.getAllTools();
```

## Available Drawing Tools (68)

### Lines

| Tool | Export | Anchors |
|------|--------|---------|
| Trend Line | `TrendLine` | 2 |
| Ray | `Ray` | 2 |
| Info Line | `InfoLine` | 2 |
| Extended Line | `ExtendedLine` | 2 |
| Trend Angle | `TrendAngle` | 2 |
| Horizontal Line | `HorizontalLine` | 1 |
| Horizontal Ray | `HorizontalRay` | 1 |
| Vertical Line | `VerticalLine` | 1 |
| Cross Line | `CrossLine` | 1 |

### Channels

| Tool | Export | Anchors |
|------|--------|---------|
| Parallel Channel | `ParallelChannel` | 3 |
| Regression Trend | `RegressionTrend` | 2 |
| Flat Top/Bottom | `FlatTopBottom` | 3 |
| Disjoint Channel | `DisjointChannel` | 4 |

### Pitchforks

| Tool | Export | Anchors |
|------|--------|---------|
| Andrews Pitchfork | `AndrewsPitchfork` | 3 |
| Schiff Pitchfork | `SchiffPitchfork` | 3 |
| Modified Schiff Pitchfork | `ModifiedSchiffPitchfork` | 3 |
| Inside Pitchfork | `InsidePitchfork` | 3 |

### Fibonacci

| Tool | Export | Anchors |
|------|--------|---------|
| Fib Retracement | `FibRetracement` | 2 |
| Fib Extension | `FibExtension` | 3 |
| Fib Channel | `FibChannel` | 3 |
| Fib Time Zone | `FibTimeZone` | 2 |
| Fib Speed Fan | `FibSpeedFan` | 2 |
| Fib Time Extension | `FibTimeExtension` | 3 |
| Fib Circles | `FibCircles` | 2 |
| Fib Spiral | `FibSpiral` | 2 |
| Fib Arcs | `FibArcs` | 2 |
| Fib Wedge | `FibWedge` | 3 |
| Pitchfan | `Pitchfan` | 3 |

### Gann

| Tool | Export | Anchors |
|------|--------|---------|
| Gann Box | `GannBox` | 2 |
| Gann Fan | `GannFan` | 2 |
| Gann Square Fixed | `GannSquareFixed` | 1 |
| Gann Square | `GannSquare` | 2 |

### Forecasting & Measurement

| Tool | Export | Anchors |
|------|--------|---------|
| Long Position | `LongPosition` | 3 |
| Short Position | `ShortPosition` | 3 |
| Forecast | `Forecast` | 2 |
| Bars Pattern | `BarsPattern` | 3 |
| Projection | `Projection` | 3 |
| Price Range | `PriceRange` | 2 |
| Date Range | `DateRange` | 2 |
| Date & Price Range | `DatePriceRange` | 2 |

### Shapes

| Tool | Export | Anchors |
|------|--------|---------|
| Rectangle | `Rectangle` | 2 |
| Rotated Rectangle | `RotatedRectangle` | 3 |
| Circle | `Circle` | 2 |
| Triangle | `Triangle` | 3 |
| Ellipse | `Ellipse` | 2 |
| Arc | `Arc` | 3 |
| Path | `Path` | 2+ |
| Polyline | `Polyline` | 2+ |
| Curve | `Curve` | 4 |
| Double Curve | `DoubleCurve` | 3 |

### Annotations

| Tool | Export | Anchors |
|------|--------|---------|
| Text | `TextAnnotation` | 1 |
| Callout | `Callout` | 2 |
| Anchored Text | `AnchoredText` | 2 |
| Note | `Note` | 1 |
| Price Note | `PriceNote` | 1 |
| Price Label | `PriceLabel` | 1 |
| Flag Mark | `FlagMark` | 1 |
| Pin | `Pin` | 1 |
| Comment | `Comment` | 1 |
| Signpost | `Signpost` | 1 |
| Table | `Table` | 1 |
| Brush | `Brush` | 2+ |
| Highlighter | `Highlighter` | 2+ |
| Arrow | `Arrow` | 2 |
| Arrow Marker | `ArrowMarker` | 1 |
| Arrow Mark Up | `ArrowMarkUp` | 1 |
| Arrow Mark Down | `ArrowMarkDown` | 1 |

## Architecture

Each drawing tool follows a two-class pattern:

- **Tool class** (e.g. `TrendLine`) - extends `Drawing`, holds anchors/state, implements hit testing and geometry computation
- **Pane view** (e.g. `TrendLinePaneView`) - implements `IPrimitivePaneView` from lightweight-charts, handles canvas rendering

The `DrawingManager` orchestrates lifecycle, selection, drag-editing, and event emission.

## License

MIT
