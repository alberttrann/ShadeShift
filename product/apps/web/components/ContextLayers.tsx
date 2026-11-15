"use client";

export type ContextLayer = "none" | "landcover" | "vegToBuilt";

export function ContextLayers({
  value,
  onChange,
}: {
  value: ContextLayer;
  onChange: (value: ContextLayer) => void;
}) {
  return (
    <div className="contextControl">
      <span>Explain selected cell</span>
      <select
        value={value}
        onChange={(event) =>
          onChange(event.target.value as ContextLayer)
        }
      >
        <option value="none">Off</option>
        <option value="landcover">10 m land cover</option>
        <option value="vegToBuilt">2017→2025 veg→built</option>
      </select>
    </div>
  );
}
