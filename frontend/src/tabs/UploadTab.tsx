import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import clsx from "clsx";
import { Card } from "../components/Card";

export function UploadTab() {
  const [files, setFiles] = useState<File[]>([]);
  const onDrop = useCallback(
    (accepted: File[]) =>
      setFiles((prev) => [...prev, ...accepted].slice(0, 50)),
    [],
  );
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      "application/octet-stream": [".frax", ".xfra", ".fra", ".sfra"],
      "text/csv": [".csv", ".tsv"],
      "text/xml": [".xml"],
    },
  });

  return (
    <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
      <Card
        title="Upload SFRA file"
        subtitle="MEGGER FRAX, Doble, Omicron, CIGRE/IEC/IEEE CSV — auto-detected"
      >
        <div
          {...getRootProps()}
          className={clsx(
            "rounded-lg border-2 border-dashed px-5 py-12 text-center transition-colors cursor-pointer",
            isDragActive
              ? "border-brand-600 bg-brand-50 dark:bg-slate-700"
              : "border-slate-300 dark:border-slate-600",
          )}
        >
          <input {...getInputProps()} />
          <div className="mb-2 text-3xl">📂</div>
          <div className="text-sm font-semibold">
            {isDragActive ? "Drop now…" : "Drop SFRA files here, or click to browse"}
          </div>
          <div
            className="mt-1 text-xs"
            style={{ color: "var(--text-tertiary)" }}
          >
            .frax · .xfra · .fra · .sfra · .csv · .tsv · .xml
          </div>
        </div>
        {files.length > 0 && (
          <div className="mt-3 space-y-1 text-sm">
            {files.map((f) => (
              <div
                key={f.name + f.size}
                className="flex items-center justify-between border-b py-1"
                style={{ borderColor: "var(--border-default)" }}
              >
                <span>{f.name}</span>
                <span
                  className="ds-mono text-xs"
                  style={{ color: "var(--text-tertiary)" }}
                >
                  {(f.size / 1024).toFixed(1)} KB
                </span>
              </div>
            ))}
            <div className="pt-2">
              <button type="button" className="ds-btn-primary">
                Parse & analyse ({files.length})
              </button>
            </div>
          </div>
        )}
      </Card>
      <Card
        title="Upload modes (spec v2 §6)"
        subtitle="Two paths — both produce identical analysis output"
      >
        <div className="space-y-3 text-sm">
          <div>
            <div className="font-semibold">Single-combination upload</div>
            <p
              className="mt-1 text-xs"
              style={{ color: "var(--text-tertiary)" }}
            >
              CSV / XML / single-sweep .frax for one combination row. Tap
              positions captured in the modal. Analysis runs immediately.
            </p>
          </div>
          <div>
            <div className="font-semibold">Batch FRAX upload</div>
            <p
              className="mt-1 text-xs"
              style={{ color: "var(--text-tertiary)" }}
            >
              One .frax holding all sweeps from a site visit. The tool
              auto-explodes into per-combination rows. Sweeps unmapped to
              the seeded combination set are flagged red for manual
              assignment.
            </p>
          </div>
          <div
            className="rounded p-3"
            style={{ background: "var(--surface-card)", color: "var(--text-secondary)" }}
          >
            <strong>Mode 2 (single-trace, no reference):</strong> tested
            traces uploaded before a reference exists in the active overhaul
            cycle still get a full analysis (qualitative). When the
            reference arrives, Mode 1 results supersede Mode 2 automatically.
          </div>
        </div>
      </Card>
    </div>
  );
}
