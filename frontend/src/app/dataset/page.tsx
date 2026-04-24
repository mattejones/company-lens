"use client";
import { useEffect, useState } from "react";
import Link from "next/link";
import { listLookups, LookupSummary } from "@/lib/api";

export default function DatasetPage() {
  const [lookups, setLookups] = useState<LookupSummary[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    listLookups().then(setLookups).finally(() => setLoading(false));
  }, []);

  const verified = lookups.filter((l) => l.verified_domain_id);
  const success = lookups.filter((l) => l.status === "success");

  return (
    <div className="animate-fade-in">
      <div className="mb-8">
        <p className="font-mono text-xs text-accent tracking-widest mb-2 uppercase">Enriched Data</p>
        <h1 className="font-display text-3xl font-700 text-text-primary">Dataset</h1>
      </div>

      <div className="grid grid-cols-3 gap-3 mb-8">
        {[
          { label: "Total lookups", value: lookups.length },
          { label: "Completed", value: success.length },
          { label: "Human verified", value: verified.length },
        ].map((s) => (
          <div key={s.label} className="bg-bg-surface border border-bg-border rounded p-4">
            <p className="font-display text-2xl font-700 text-accent">{s.value}</p>
            <p className="font-mono text-xs text-text-muted mt-1">{s.label}</p>
          </div>
        ))}
      </div>

      {loading ? (
        <div className="text-center py-16">
          <div className="w-5 h-5 border border-accent/40 border-t-accent rounded-full animate-spin mx-auto" />
        </div>
      ) : lookups.length === 0 ? (
        <div className="border border-dashed border-bg-border rounded p-16 text-center">
          <p className="font-mono text-xs text-text-muted">
            No data yet —{" "}
            <Link href="/" className="text-accent hover:underline">enrich a company</Link> to get started
          </p>
        </div>
      ) : (
        <div className="stagger space-y-2">
          {lookups.map((l) => <LookupRow key={l.lookup_id} lookup={l} />)}
        </div>
      )}
    </div>
  );
}

function LookupRow({ lookup: l }: { lookup: LookupSummary }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div className="bg-bg-surface border border-bg-border rounded hover:border-accent/20 transition-all">
      <div className="p-4 flex items-start gap-4">
        <div className="min-w-0 flex-1">
          {/* Status + badges row */}
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <div className={`status-dot ${l.status === "success" ? "success" : l.status === "failure" ? "failure" : "pending"}`} />
            <span className="font-mono text-[10px] text-text-muted">{l.status}</span>
            {l.verified_domain_id && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-status-success/30 text-status-success bg-status-success/10">
                ✓ verified
              </span>
            )}
          </div>

          {/* Company name */}
          <p className="font-display font-500 text-text-primary text-sm">{l.company_name ?? "—"}</p>

          {/* Primary domain — always visible when present */}
          {l.primary_domain ? (
            <a
              href={`https://${l.primary_domain}`}
              target="_blank"
              rel="noopener noreferrer"
              className="font-mono text-sm text-accent hover:underline mt-0.5 inline-block"
            >
              {l.primary_domain} ↗
            </a>
          ) : l.status === "success" ? (
            <span className="font-mono text-xs text-text-muted mt-0.5 inline-block">No domain identified</span>
          ) : null}

          {/* Meta row */}
          <div className="flex flex-wrap gap-x-4 gap-y-0.5 mt-1">
            <span className="font-mono text-[10px] text-text-muted">{l.company_number}</span>
            {l.completed_at && (
              <span className="font-mono text-[10px] text-text-muted">{new Date(l.completed_at).toLocaleString()}</span>
            )}
            <span className="font-mono text-[10px] text-text-muted truncate max-w-xs">ID: {l.lookup_id}</span>
          </div>
        </div>

        <div className="shrink-0 flex items-center gap-2 pt-0.5">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="px-3 py-1.5 text-xs font-mono text-text-muted border border-bg-border hover:border-accent/30 hover:text-text-secondary rounded transition-all"
          >
            {expanded ? "Less ▲" : "Raw ▼"}
          </button>
          {l.status === "success" && (
            <Link
              href={`/lookups/${l.lookup_id}`}
              className="px-4 py-2 border border-accent/30 text-accent text-xs font-mono rounded hover:bg-accent/10 transition-all"
            >
              Detail →
            </Link>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-bg-border px-4 py-3">
          <pre className="text-[11px] font-mono text-text-secondary leading-relaxed overflow-x-auto whitespace-pre-wrap break-all">
            {JSON.stringify(l, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}
