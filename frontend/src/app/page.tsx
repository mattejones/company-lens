"use client";
import { useState, useMemo, useRef, useEffect } from "react";
import { searchCompanies, triggerEnrichment, CHCompany } from "@/lib/api";

type JobState = { jobId: string; status: string };

export default function Home() {
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<CHCompany[]>([]);
  const [loading, setLoading] = useState(false);
  const [jobs, setJobs] = useState<Record<string, JobState>>({});
  const [activeOnly, setActiveOnly] = useState(false);
  const [sicFilter, setSicFilter] = useState("");
  const [sicOpen, setSicOpen] = useState(false);

  async function handleSearch(e: React.FormEvent) {
    e.preventDefault();
    if (!query.trim()) return;
    setLoading(true);
    try {
      const data = await searchCompanies(query, 20);
      setResults(data.items ?? []);
    } catch {
      setResults([]);
    } finally {
      setLoading(false);
    }
  }

  async function handleEnrich(company: CHCompany) {
    const num = company.company_number;
    setJobs((j) => ({ ...j, [num]: { jobId: "", status: "dispatching" } }));
    try {
      const { job_id } = await triggerEnrichment(num);
      setJobs((j) => ({ ...j, [num]: { jobId: job_id, status: "pending" } }));
    } catch {
      setJobs((j) => ({ ...j, [num]: { jobId: "", status: "error" } }));
    }
  }

  const filtered = useMemo(() => results.filter((c) => {
    if (activeOnly && c.company_status !== "active") return false;
    if (sicFilter.trim() && !c.sic_codes?.some((s) => s.includes(sicFilter.trim()))) return false;
    return true;
  }), [results, activeOnly, sicFilter]);

  // SIC codes present in results — used for autocomplete dropdown
  const availableSics = useMemo(() => {
    const all = results.flatMap((c) => c.sic_codes ?? []);
    return [...new Set(all)].sort();
  }, [results]);

  const sicSuggestions = availableSics.filter(
    (s) => sicFilter && s.includes(sicFilter) && s !== sicFilter
  );

  return (
    <div className="animate-fade-in">
      <div className="mb-12">
        <p className="font-mono text-xs text-accent tracking-widest mb-3 uppercase">Companies House → Domain Intelligence</p>
        <h1 className="font-display text-4xl font-800 text-text-primary leading-tight mb-4">
          Find a company.<br /><span className="text-accent">Discover its domain.</span>
        </h1>
        <p className="text-text-secondary text-sm max-w-lg">
          Search the Companies House register, enrich with LLM-powered domain inference,
          and verify results through DNS, WHOIS, and content signals.
        </p>
      </div>

      <form onSubmit={handleSearch} className="mb-4 flex gap-3">
        <div className="relative flex-1">
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search by company name or registration number..."
            className="w-full bg-bg-surface border border-bg-border rounded px-4 py-3 text-sm text-text-primary placeholder-text-muted focus:outline-none focus:border-accent/50 transition-all font-mono"
          />
          {loading && (
            <div className="absolute right-3 top-1/2 -translate-y-1/2">
              <div className="w-4 h-4 border border-accent/40 border-t-accent rounded-full animate-spin" />
            </div>
          )}
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-6 py-3 bg-accent text-bg-base text-xs font-mono font-500 tracking-wider rounded hover:bg-accent/90 disabled:opacity-50 transition-colors"
        >
          SEARCH
        </button>
      </form>

      {results.length > 0 && (
        <div className="flex items-center gap-4 mb-6 p-3 bg-bg-surface border border-bg-border rounded">
          {/* Toggle — fixed: clickable area is the whole label, no nested button */}
          <label className="flex items-center gap-2 cursor-pointer select-none shrink-0">
            <input
              type="checkbox"
              checked={activeOnly}
              onChange={(e) => setActiveOnly(e.target.checked)}
              className="sr-only"
            />
            <div
              className={`w-8 h-4 rounded-full transition-colors relative shrink-0 ${activeOnly ? "bg-accent" : "bg-bg-border"}`}
            >
              <span
                className={`absolute top-0.5 w-3 h-3 rounded-full bg-white transition-transform duration-200 ${activeOnly ? "translate-x-4" : "translate-x-0.5"}`}
              />
            </div>
            <span className="font-mono text-xs text-text-secondary whitespace-nowrap">Active only</span>
          </label>

          <div className="w-px h-4 bg-bg-border shrink-0" />

          {/* SIC autocomplete */}
          <div className="flex items-center gap-2 flex-1 relative">
            <span className="font-mono text-xs text-text-muted shrink-0">SIC</span>
            <div className="relative flex-1">
              <input
                value={sicFilter}
                onChange={(e) => { setSicFilter(e.target.value); setSicOpen(true); }}
                onFocus={() => setSicOpen(true)}
                onBlur={() => setTimeout(() => setSicOpen(false), 150)}
                placeholder={availableSics.length ? `e.g. ${availableSics[0]}` : "e.g. 62012"}
                className="w-full bg-bg-elevated border border-bg-border rounded px-3 py-1.5 text-xs text-text-primary placeholder-text-muted font-mono focus:outline-none focus:border-accent/40 transition-all"
              />
              {sicOpen && sicSuggestions.length > 0 && (
                <div className="absolute top-full left-0 right-0 mt-1 bg-bg-elevated border border-bg-border rounded shadow-lg z-20 overflow-hidden">
                  {sicSuggestions.map((s) => (
                    <button
                      key={s}
                      type="button"
                      onMouseDown={() => { setSicFilter(s); setSicOpen(false); }}
                      className="w-full text-left px-3 py-2 font-mono text-xs text-text-secondary hover:bg-bg-surface hover:text-accent transition-colors"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
            {sicFilter && (
              <button
                type="button"
                onClick={() => setSicFilter("")}
                className="text-text-muted hover:text-text-secondary font-mono text-xs shrink-0"
              >
                ✕
              </button>
            )}
          </div>

          <div className="w-px h-4 bg-bg-border shrink-0" />
          <span className="font-mono text-xs text-text-muted shrink-0">{filtered.length} / {results.length}</span>
        </div>
      )}

      {filtered.length > 0 && (
        <div className="stagger space-y-2">
          {filtered.map((c) => (
            <CompanyRow key={c.company_number} company={c} job={jobs[c.company_number]} onEnrich={() => handleEnrich(c)} />
          ))}
        </div>
      )}

      {!loading && results.length > 0 && filtered.length === 0 && (
        <p className="text-text-muted text-sm font-mono text-center py-12">No results match the current filters</p>
      )}
      {!loading && results.length === 0 && query && (
        <p className="text-text-muted text-sm font-mono text-center py-16">No results for &quot;{query}&quot;</p>
      )}
      {results.length === 0 && !query && (
        <div className="border border-dashed border-bg-border rounded p-16 text-center">
          <p className="font-mono text-xs text-text-muted">Search Companies House to get started</p>
        </div>
      )}
    </div>
  );
}

function CompanyRow({ company: c, job, onEnrich }: { company: CHCompany; job?: JobState; onEnrich: () => void }) {
  const [expanded, setExpanded] = useState(false);
  const name = c.company_name ?? c.title ?? "Unknown";
  const address = c.registered_office_address;

  return (
    <div className="bg-bg-surface border border-bg-border rounded hover:border-accent/20 transition-all">
      <div className="p-4 flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <span className="font-mono text-xs text-accent/70">{c.company_number}</span>
            <StatusBadge status={c.company_status} />
            {c.type && (
              <span className="text-[10px] font-mono px-1.5 py-0.5 rounded border border-bg-border text-text-muted">
                {c.type.replace(/_/g, " ")}
              </span>
            )}
          </div>
          <p className="font-display font-500 text-text-primary text-sm mb-1">{name}</p>
          <div className="flex flex-wrap gap-x-4 gap-y-0.5">
            {address?.address_line_1 && <span className="text-xs text-text-muted">{address.address_line_1}</span>}
            {address?.locality && <span className="text-xs text-text-muted">{address.locality}</span>}
            {address?.postal_code && <span className="text-xs font-mono text-text-muted">{address.postal_code}</span>}
            {c.date_of_creation && <span className="text-xs font-mono text-text-muted">Inc. {c.date_of_creation}</span>}
          </div>
          {c.sic_codes && c.sic_codes.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {c.sic_codes.map((sic) => (
                <span key={sic} className="font-mono text-[10px] px-1.5 py-0.5 bg-bg-elevated border border-bg-border rounded text-text-secondary">
                  {sic}
                </span>
              ))}
            </div>
          )}
        </div>

        <div className="shrink-0 flex items-center gap-2 pt-0.5">
          <button
            onClick={() => setExpanded((e) => !e)}
            className="px-3 py-1.5 text-xs font-mono text-text-muted border border-bg-border hover:border-accent/30 hover:text-text-secondary rounded transition-all"
          >
            {expanded ? "Less ▲" : "All data ▼"}
          </button>
          {!job ? (
            <button onClick={onEnrich} className="px-4 py-2 border border-accent/30 text-accent text-xs font-mono rounded hover:bg-accent/10 transition-all">
              Enrich →
            </button>
          ) : job.status === "dispatching" ? (
            <span className="text-xs font-mono text-text-muted">Dispatching...</span>
          ) : job.status === "error" ? (
            <span className="text-xs font-mono text-status-failure">Error</span>
          ) : (
            <div className="flex items-center gap-2">
              <div className="status-dot pending" />
              <span className="text-xs font-mono text-status-pending">Queued</span>
            </div>
          )}
        </div>
      </div>

      {expanded && (
        <div className="border-t border-bg-border px-4 py-3">
          <pre className="text-[11px] font-mono text-text-secondary leading-relaxed overflow-x-auto whitespace-pre-wrap break-all">
            {JSON.stringify(c, null, 2)}
          </pre>
        </div>
      )}
    </div>
  );
}

function StatusBadge({ status }: { status?: string }) {
  const styles: Record<string, string> = {
    active: "border-status-success/30 text-status-success bg-status-success/10",
    dissolved: "border-status-failure/30 text-status-failure bg-status-failure/10",
    "in-administration": "border-status-pending/30 text-status-pending bg-status-pending/10",
  };
  const s = status ?? "unknown";
  return (
    <span className={`text-[10px] font-mono px-1.5 py-0.5 rounded border ${styles[s] ?? "border-text-muted/30 text-text-muted"}`}>
      {s}
    </span>
  );
}
