"use client";

export type GlobalSurfaceLayer =
  | "none"
  | "landcover"
  | "vegToBuilt";

export type GlobalSurfaceStatus =
  | "idle"
  | "loading"
  | "ready"
  | "error";

export function SurfaceLayers({
  open,
  value,
  status,
  onOpenChange,
  onChange,
}: {
  open: boolean;
  value: GlobalSurfaceLayer;
  status: GlobalSurfaceStatus;
  onOpenChange: (open: boolean) => void;
  onChange: (value: GlobalSurfaceLayer) => void;
}) {
  const statusLabel =
    status === "loading"
      ? "LOADING"
      : status === "error"
        ? "ERROR"
        : value !== "none" && status === "ready"
          ? "ON"
          : null;

  return (
    <div className="surfaceLayerWrap">
      <button
        className={`surfaceLayerButton ${value !== "none" ? "active" : ""}`}
        onClick={() => onOpenChange(!open)}
        aria-expanded={open}
      >
        <span className="layerGlyph" aria-hidden="true">
          <i />
          <i />
          <i />
        </span>
        <span>Surface layers</span>
        {statusLabel && (
          <b className={`surfaceStatus surfaceStatus-${status}`}>
            {statusLabel}
          </b>
        )}
      </button>

      {open && (
        <div className="surfaceLayerMenu panel">
          <div className="surfaceMenuHead">
            <span>WHOLE-PILOT EVIDENCE</span>
            <strong>Inspect the surface across the AOI</strong>
            <p>
              These overlays explain the satellite-derived surface evidence.
              They never change a planning score or rank.
            </p>
          </div>

          {status === "error" && (
            <div className="surfaceError">
              Global raster assets are unavailable. Re-run the v2.1 product
              repair so the whole-AOI layers are exported and verified.
            </div>
          )}

          <button
            className={value === "none" ? "active" : ""}
            onClick={() => onChange("none")}
          >
            <span className="surfaceIcon surfaceNone">×</span>
            <div>
              <strong>Planning map</strong>
              <small>Show the active 500 m analytical view.</small>
            </div>
          </button>

          <button
            className={value === "landcover" ? "active" : ""}
            onClick={() => onChange("landcover")}
          >
            <span className="surfaceIcon surfaceLand" aria-hidden="true">
              <i />
              <i />
              <i />
            </span>
            <div>
              <strong>10 m land cover</strong>
              <small>
                Reliable vegetation, built, and water evidence across the
                full source footprint.
              </small>
            </div>
          </button>

          <button
            className={value === "vegToBuilt" ? "active" : ""}
            onClick={() => onChange("vegToBuilt")}
          >
            <span className="surfaceIcon surfaceHistory">17→25</span>
            <div>
              <strong>Historical vegetation → built</strong>
              <small>
                Reliable 2017→2025 transition support across the jointly
                reliable subset.
              </small>
            </div>
          </button>
        </div>
      )}
    </div>
  );
}
