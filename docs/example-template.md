# Example SVG template

`template_path` must point at an existing SVG. The root element needs `width`, `height`, and `viewBox`.

Slots are placeholders that get replaced when a plot is rendered. Each slot must:

- have an `id` that matches a config field (`title_slot`, `chart_slot`, `ranking_slot`, or an `against` `chart_slot`)
- be a leaf shape (`rect`, `path`, etc.) with a positive bounding box
- not be a group with children

The following ranking template example matches the slot ids in [example-config.md](example-config.md):

```svg
<svg xmlns="http://www.w3.org/2000/svg" width="1080" height="1920" viewBox="0 0 1080 1920">
  <rect id="title" x="40" y="40" width="1000" height="80"/>
  <rect id="slot1" x="40" y="160" width="1000" height="700"/>
  <rect id="slot2" x="40" y="900" width="1000" height="960"/>
</svg>
```

Fill on a slot is optional; the placeholder is discarded when the title, chart, or table is embedded.
