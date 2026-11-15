"use client";

import type { PriorityListItemDto } from "@shadeshift/contracts";

export function TopList({
  items,
  strongItems,
  selectedCellId,
  strongEvidenceOnly,
  onStrongEvidenceOnlyChange,
  onSelect,
  onClose,
}: {
  items: PriorityListItemDto[];
  strongItems: PriorityListItemDto[];
  selectedCellId: string | null;
  strongEvidenceOnly: boolean;
  onStrongEvidenceOnlyChange: (value: boolean) => void;
  onSelect: (id: string) => void;
  onClose: () => void;
}) {
  const visible = strongEvidenceOnly ? strongItems : items;

  return (
    <aside className="shortlistDrawer panel">
      <div className="shortlistHead">
        <div>
          <span className="eyebrow">PRIORITY SHORTLIST</span>
          <h3>Priority shortlist</h3>
        </div>
        <button onClick={onClose} aria-label="Close shortlist">
          ×
        </button>
      </div>

      <label className="shortlistFilter">
        <input
          type="checkbox"
          checked={strongEvidenceOnly}
          onChange={(event) =>
            onStrongEvidenceOnlyChange(event.target.checked)
          }
        />
        <span>
          Strong evidence only
          <small>
            Uses the independent high-confidence shortlist; priority scores are
            unchanged.
          </small>
        </span>
      </label>

      <div className="shortlistBody">
        {visible.map((item) => (
          <button
            key={item.cellId}
            className={`topItem ${
              selectedCellId === item.cellId ? "selected" : ""
            }`}
            onClick={() => {
              onSelect(item.cellId);
              onClose();
            }}
          >
            <span className="rank">
              {strongEvidenceOnly &&
              item.highConfidencePriorityRank
                ? `#${item.highConfidencePriorityRank}`
                : `#${item.priorityRank}`}
            </span>

            <span className="topCellMain">
              <strong>{item.cellId}</strong>
              <small>
                Heat {Math.round(item.heatScore * 100)}th · Greening{" "}
                {Math.round(item.greeningNeed * 100)}%
              </small>
            </span>

            <span
              className={`miniGrade grade${
                item.evidence.grade ?? "Unknown"
              }`}
            >
              {item.evidence.grade ?? "—"}
            </span>
          </button>
        ))}
      </div>
    </aside>
  );
}
