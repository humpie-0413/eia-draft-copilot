"use client";

import { ChevronDown, ChevronUp, Layers } from "lucide-react";
import { useState } from "react";
import type { LayerDef } from "./use-map-layers";

interface LayerControlProps {
  layers: LayerDef[];
  onToggle: (layerId: string) => void;
}

/**
 * 레이어 토글 체크박스 패널.
 * 접기/펼치기 지원.
 */
export function LayerControl({ layers, onToggle }: LayerControlProps) {
  const [collapsed, setCollapsed] = useState(false);

  return (
    <div className="rounded-lg border bg-white shadow-md">
      {/* 헤더 */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="flex w-full items-center justify-between px-3 py-2 text-sm font-medium hover:bg-gray-50"
      >
        <span className="flex items-center gap-1.5">
          <Layers className="h-4 w-4" />
          레이어
        </span>
        {collapsed ? (
          <ChevronDown className="h-4 w-4" />
        ) : (
          <ChevronUp className="h-4 w-4" />
        )}
      </button>

      {/* 레이어 목록 */}
      {!collapsed && (
        <div className="border-t px-3 py-2 space-y-1">
          {layers.map((layer) => (
            <label
              key={layer.id}
              className="flex cursor-pointer items-center gap-2 rounded px-1 py-1 text-sm hover:bg-gray-50"
            >
              <input
                type="checkbox"
                checked={layer.visible}
                disabled={layer.alwaysOn}
                onChange={() => onToggle(layer.id)}
                className="h-3.5 w-3.5 rounded border-gray-300 accent-current"
                style={{ accentColor: layer.color }}
              />
              {/* 범례 색상 */}
              <span
                className="inline-block h-3 w-3 rounded-sm border border-gray-200"
                style={{ backgroundColor: layer.color }}
              />
              <span className={layer.alwaysOn ? "text-gray-700" : ""}>
                {layer.label}
              </span>
              {layer.alwaysOn && (
                <span className="ml-auto text-[10px] text-gray-400">항상</span>
              )}
            </label>
          ))}
        </div>
      )}
    </div>
  );
}
